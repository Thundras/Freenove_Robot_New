import os
import warnings
import logging

# 0. Deep silence for AI libraries (MUST be at the very top)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TFLITE_LOG_SEVERITY'] = '3'
os.environ['GLOG_minloglevel'] = '3'

# Suppress Python-level warnings
warnings.filterwarnings("ignore")

# Pre-emptive logger silencing
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('keras').setLevel(logging.ERROR)
logging.getLogger('absl').setLevel(logging.WARNING)

import multiprocessing
import time
import numpy as np
import math

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision as mp_vision
except ImportError:
    mp = None

# TFLite for Object Detection
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    try:
        import tensorflow.lite as tflite
    except ImportError:
        tflite = None

logger = logging.getLogger(__name__)

class ObjectDetector:
    """Handles TFLite Object Detection (Person/Pet)"""
    def __init__(self, model_path, label_path):
        self.interpreter = None
        self.labels = {}
        if tflite:
            self.interpreter = tflite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            # Load labels
            with open(label_path, 'r') as f:
                for i, line in enumerate(f):
                    self.labels[i] = line.strip()

    def detect(self, frame):
        if not self.interpreter:
            return []

        # 1. Preprocess Frame
        h, w, _ = frame.shape
        input_shape = self.input_details[0]['shape'] # [1, 300, 300, 3]
        input_data = cv2.resize(frame, (input_shape[2], input_shape[1]))
        input_data = np.expand_dims(input_data, axis=0)

        # 2. Run Inference
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()

        # 3. Get results
        boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0] # [N, 4]
        classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0] # [N]
        scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0] # [N]

        detections = []
        for i in range(len(scores)):
            if scores[i] > 0.5: # Confidence threshold
                label = self.labels.get(int(classes[i]), "unknown")
                detections.append({
                    "label": label,
                    "score": float(scores[i]),
                    "box": boxes[i].tolist() # [ymin, xmin, ymax, xmax]
                })
        return detections

class FaceAnalyzer:
    """Uses YuNet for detection and SFace for recognition"""
    def __init__(self, detector_path, recognizer_path):
        self.detector = None
        self.recognizer = None
        if cv2:
            try:
                self.detector = cv2.FaceDetectorYN.create(detector_path, "", (320, 320))
                self.recognizer = cv2.FaceRecognizerSF.create(recognizer_path, "")
            except Exception as e:
                logger.error(f"Failed to initialize FaceAnalyzer: {e}")

    def analyze(self, frame, box):
        """
        Detects and encodes a face within a specific person box
        box: [ymin, xmin, ymax, xmax] (normalized)
        Returns: (embedding, face_jpg_bytes, face_box_norm) or (None, None, None)
        """
        if not self.detector or not self.recognizer or frame is None:
            return None, None, None
            
        try:
            h, w = frame.shape[:2]
            ymin, xmin, ymax, xmax = box
            left, top, right, bottom = int(xmin*w), int(ymin*h), int(xmax*w), int(ymax*h)
            
            # Crop person area with some padding
            pad = 20
            top_pad, left_pad = max(0, top-pad), max(0, left-pad)
            person_crop = frame[top_pad:min(h, bottom+pad), left_pad:min(w, right+pad)]
            if person_crop.size == 0 or person_crop.shape[0] < 10 or person_crop.shape[1] < 10:
                return None, None, None
                
            # Detect face in crop
            self.detector.setInputSize((person_crop.shape[1], person_crop.shape[0]))
            _, faces = self.detector.detect(person_crop)
            
            if faces is not None and len(faces) > 0:
                # Take the largest face
                face = faces[0]
                # face[0:2] = x, y (top-left of face relative to person_crop)
                # face[2:4] = w, h
                fx_crop, fy_crop, fw_crop, fh_crop = face[0:4]
                
                # Convert back to overall frame coordinates
                fx_total = left_pad + fx_crop
                fy_total = top_pad + fy_crop
                
                # Normalize face box: [ymin, xmin, ymax, xmax]
                face_box_norm = [
                    float(fy_total / h),
                    float(fx_total / w),
                    float((fy_total + fh_crop) / h),
                    float((fx_total + fw_crop) / w)
                ]

                # Align and recognize
                aligned = self.recognizer.alignCrop(person_crop, face)
                if aligned is not None and aligned.size > 0:
                    feature = self.recognizer.feature(aligned)
                    _, buffer = cv2.imencode('.jpg', aligned)
                    return feature.flatten().tolist(), buffer.tobytes(), face_box_norm
        except Exception as e:
            logger.debug(f"FaceAnalyzer error: {e}")
            
        return None, None, None

class VisionProcess(multiprocessing.Process):
    def __init__(self, result_queue: multiprocessing.Queue, frame_queue: multiprocessing.Queue, config, shared_imu=None, identity_queue=None, shared_flags=None):
        """
        Runs in a separate process to avoid blocking the high-frequency motor control loop.
        :param result_queue: Queue to send detection results back to the brain.
        :param frame_queue: Queue to send raw frames to the web server for streaming.
        :param identity_queue: Queue to receive recognized names from the brain.
        :param shared_flags: Shared array for real-time config toggles [show_debug, soft_stab, ...]
        """
        super().__init__()
        self.result_queue = result_queue
        self.frame_queue = frame_queue
        self.identity_queue = identity_queue
        self.config = config
        self.shared_flags = shared_flags
        self.running = multiprocessing.Event()
        self.running.set() # Set to True by default
        self.current_identity = None 
        
        # Load Camera Tilt Config
        camera_cfg = self.config.get("servos.camera.tilt", {})
        self.tilt_channel = camera_cfg.get("channel", 14)
        self.tilt_angle = camera_cfg.get("middle", 90)
        self.tilt_min = camera_cfg.get("min", 45)
        self.tilt_max = camera_cfg.get("max", 135)
        self.shared_imu = shared_imu
        self.mechanical_stab = self.config.get("system.camera_stabilization", True)
        self.software_stab = self.config.get("system.camera_stabilization", True)
        self.stab_crop = self.config.get("system.camera_stabilization_crop", 0.15) # 15% crop for DIS
        self.last_tilt_update = time.time()

    def stop(self):
        logger.info("VisionProcess.stop() called")
        self.running.clear()

    def transform_coords(self, x, y, M, cw, ch, sw, sh):
        """Helper to map original frame coords to stabilized/cropped frame"""
        # 1. Apply perspective/rotation matrix
        nx = M[0, 0] * x + M[0, 1] * y + M[0, 2]
        ny = M[1, 0] * x + M[1, 1] * y + M[1, 2]
        # 2. Subtract Crop offset and Scale
        return (nx - cw) * sw, (ny - ch) * sh

    def run(self):
        # Do NOT call self.running.set() here, it might override a stop request
        
        # --- SUBPROCESS LOGGING SETUP (Windows Compatibility) ---
        import sys
        import warnings
        
        # Suppress Python-level warnings in this process too
        warnings.filterwarnings("ignore")
        
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        if not root.handlers:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            root.addHandler(ch)
            
        # Silence library noise in the subprocess
        logging.getLogger('absl').setLevel(logging.ERROR)
        logging.getLogger('tensorflow').setLevel(logging.ERROR)
        
        logger.info("Vision process started (Real AI Mode)")
        
        # MediaPipe Tasks for Gestures
        hand_landmarker = None
        if mp is not None:
            try:
                model_path = os.path.join(os.path.dirname(__file__), "models", "hand_landmarker.task")
                base_options = python.BaseOptions(model_asset_path=model_path)
                options = mp_vision.HandLandmarkerOptions(
                    base_options=base_options,
                    running_mode=mp_vision.RunningMode.VIDEO,
                    num_hands=1,
                    min_hand_detection_confidence=0.45, # Lowered to speed up discovery
                    min_hand_presence_confidence=0.6,
                    min_tracking_confidence=0.6
                )
                hand_landmarker = mp_vision.HandLandmarker.create_from_options(options)
                if hand_landmarker:
                    logger.info("MediaPipe HandLandmarker loaded successfully (Tasks API).")
                else:
                    logger.error("MediaPipe HandLandmarker initialization returned None.")
            except Exception as e:
                logger.error(f"Failed to load MediaPipe HandLandmarker: {e}")

        # Aruco Setup
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        aruco_params = cv2.aruco.DetectorParameters()
        aruco_detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

        # Marker Registry for Distance Estimation
        marker_config = self.config.get("mapping.markers", {})

        # TFLite for Object Detection (Person/Pet)
        detector = None
        model_path = "brain/models/coco_ssd_mobilenet.tflite"
        label_path = "brain/models/labelmap.txt"
        try:
            detector = ObjectDetector(model_path, label_path)
            if detector and detector.interpreter:
                logger.info("TFLite Object Detector loaded successfully.")
            else:
                logger.error("TFLite Object Detector failed to initialize (Interpreter missing).")
        except Exception as e:
            logger.error(f"Failed to load TFLite Detector: {e}")

        # 2. Initialize Camera
        cap = None
        if cv2 is not None:
            # Try camera 0 (Pi Cam usually)
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        
        frame_count = 0
        processing_skip = self.config.get("system.vision_processing_skip", 1)
        last_positions = {}
        
        # Persistence cache for visualization
        viz_state = {
            "ball": None,    # (x, y, radius)
            "gesture": None, # (label, timestamp)
            "objects": [],   # List of (label, dist, box, color)
            "landmarks": None # (ids, corners)
        }
        
        # --- FACE ANALYZER ---
        face_detector_path = os.path.join(os.path.dirname(__file__), "models", "face_detection_yunet.onnx")
        face_recognizer_path = os.path.join(os.path.dirname(__file__), "models", "face_recognition_sface.onnx")
        face_analyzer = FaceAnalyzer(face_detector_path, face_recognizer_path)

        # Pre-initialize variables used in the loop
        soft_stab = self.software_stab
        remap_params = None
        
        parent_pid = os.getppid()
        while self.running.is_set():
            # Check for stop request or orphan state
            if not self.running.is_set() or os.getppid() != parent_pid: 
                break
            
            frame_count += 1
            if frame_count % 200 == 0:
                logger.info(f"Vision loop tick: {frame_count}")
            frame = None
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue
                
                if frame_count % 100 == 0:
                    logger.debug(f"Vision loop active. Frames processed: {frame_count}")

            if frame is not None:
                h_frame, w_frame = frame.shape[:2]
                
                # Update identity if feedback received
                if self.identity_queue and not self.identity_queue.empty():
                    try:
                        self.current_identity = self.identity_queue.get_nowait()
                    except: pass

                try:
                    do_ai = (frame_count % processing_skip == 0)
                    if do_ai:
                        # --- Red HSV Mask (Validator Only) ---
                        # Used by AI block below to confirm color
                        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                        mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
                        mask2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
                        mask = cv2.add(mask1, mask2)
                        mask = cv2.erode(mask, None, iterations=1) # Reduced to preserve smaller objects
                        mask = cv2.dilate(mask, None, iterations=1)

                    # --- AI STEP 0.5: Aruco Landmark Detection ---
                    if do_ai and aruco_detector is not None:
                        corners, ids, rejected = aruco_detector.detectMarkers(frame)
                        viz_state["landmarks"] = (ids, corners) if ids is not None else None
                        
                        if ids is not None:
                            for i, marker_id in enumerate(ids.flatten()):
                                # Get physical size from config or default to 100mm
                                m_id_str = str(marker_id)
                                phys_size = 100.0
                                if m_id_str in marker_config:
                                    phys_size = marker_config[m_id_str].get("size", 100.0)
                                
                                # 3D Pose Estimation (solvePnP)
                                # Define 3D object points for the marker (centered at origin)
                                hs = phys_size / 2.0
                                obj_pts = np.array([
                                    [-hs, hs, 0],
                                    [hs, hs, 0],
                                    [hs, -hs, 0],
                                    [-hs, -hs, 0]
                                ], dtype=np.float32)
                                
                                # Default camera matrix for 320x240 (approximate)
                                cam_matrix = np.array([
                                    [300, 0, 160],
                                    [0, 300, 120],
                                    [0, 0, 1]
                                ], dtype=np.float32)
                                dist_coeffs = np.zeros((4,1))
                                
                                marker_corners_2d = corners[i][0].astype(np.float32)
                                success, rvec, tvec = cv2.solvePnP(obj_pts, marker_corners_2d, cam_matrix, dist_coeffs)
                                
                                if success:
                                    # distance is the norm of translation vector
                                    distance_mm = np.linalg.norm(tvec)
                                    
                                    # relative angle (yaw) to marker center in camera frame
                                    # tvec[0] is X (horizontal), tvec[2] is Z (depth)
                                    angle_rel = math.atan2(tvec[0], tvec[2])
                                    
                                    # Experimental: Calculate marker's own rotation (yaw) relative to robot
                                    # This helps in knowing if the robot is looking at the marker at an angle
                                    rmat, _ = cv2.Rodrigues(rvec)
                                    # Marker's yaw relative to camera
                                    marker_yaw_rel = math.atan2(-rmat[0, 2], rmat[2, 2])
                                    
                                    try:
                                        # Correct angle for stabilized frame
                                        corner_center = np.mean(marker_corners_2d, axis=0) # [x, y]
                                        if soft_stab and remap_params:
                                            stabilized_center = self.transform_coords(corner_center[0], corner_center[1], *remap_params)
                                            # Re-estimate angle relative to center of stabilized frame
                                            # cam_matrix[0,2] is the center_x
                                            angle_rel = math.atan2(stabilized_center[0] - cam_matrix[0, 2], cam_matrix[0, 0])

                                        if self.result_queue.full(): self.result_queue.get_nowait()
                                        self.result_queue.put_nowait({
                                            "type": "landmark",
                                            "id": int(marker_id),
                                            "dist": distance_mm,
                                            "angle": angle_rel,
                                            "marker_yaw": marker_yaw_rel # Orientation of the marker itself
                                        })
                                    except Exception: pass

                    # --- AI STEP 1: Gesture Recognition (MediaPipe Tasks API) ---
                    if do_ai and hand_landmarker is not None:
                        # MediaPipe Tasks expects mp.Image
                        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        
                        # In VIDEO mode, we need a unique timestamp (ms)
                        timestamp_ms = int(time.time() * 1000)
                        results = hand_landmarker.detect_for_video(mp_image, timestamp_ms)
                        
                        if results.hand_landmarks:
                            for i, hand_landmarks in enumerate(results.hand_landmarks):
                                # Check handedness score for this specific hand

                                # 1. Count fingers (Distance-Ratio logic)
                                fingers = []
                                wrist = hand_landmarks[0]
                                for tip_id in [8, 12, 16, 20]:
                                    tip = hand_landmarks[tip_id]
                                    knuckle = hand_landmarks[tip_id - 2]
                                    dist_tip = ((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2)**0.5
                                    dist_knuckle = ((knuckle.x - wrist.x)**2 + (knuckle.y - wrist.y)**2)**0.5
                                    if dist_tip > dist_knuckle * 1.2:
                                        fingers.append(1)
                                
                                count = sum(fingers)
                                
                                # Conditional Strictness:
                                # We only process if the hand detection is solid.
                                # Finger gestures (1+) are harder to fake for the AI, so we allow lower scores.
                                # Fist gestures (0) are easily faked by background noise, so we require 75%+.
                                if results.handedness:
                                    score = results.handedness[i][0].score
                                    min_req = 0.75 if count == 0 else 0.5
                                    if score < min_req: 
                                        continue

                                label = None 
                                if count >= 3:
                                    label = "COME" # Open hand
                                elif count == 2:
                                    label = "SIT" # Peace sign
                                elif count == 1:
                                    label = "DOWN" # Pointing
                                elif count == 0:
                                    label = "AWAY" # Fist
                                
                                if label:
                                    # Log inside vision process for debugging
                                    logger.info(f"Gesture recognized: {label} (Fingers: {fingers})")
                                    try:
                                        if self.result_queue.full():
                                            self.result_queue.get_nowait()
                                        self.result_queue.put_nowait({
                                            "type": "gesture",
                                            "label": label,
                                            "confidence": 0.95,
                                            "timestamp": time.time()
                                        })
                                    except Exception: pass
                                    
                                    # Cache for visualization
                                    viz_state["gesture"] = (label, time.time())

                    # --- AI STEP 2: Object Detection (TFLite) ---
                    if do_ai and detector is not None:
                        detections = detector.detect(frame)
                        now = time.time()
                        viz_objects_new = []
                        
                        ball_found = False
                        # Pre-process AI detections for Ball candidates (Tier 1)
                        # Create a new list to hold processed detections, as we might modify 'detections' later
                        processed_detections = []
                        for d in detections:
                            if d["label"] in ["sports ball", "apple", "orange"]:
                                # Color Filter: Ensure the ball is RED
                                ymin_b, xmin_b, ymax_b, xmax_b = d["box"]
                                py1, px1 = int(ymin_b * h_frame), int(xmin_b * w_frame)
                                py2, px2 = int(ymax_b * h_frame), int(xmax_b * w_frame)
                                py1, py2 = max(0, py1), min(h_frame, py2)
                                px1, px2 = max(0, px1), min(w_frame, px2)
                                
                                if py2 > py1 and px2 > px1:
                                    # 1. Broad Density Check
                                    box_mask = mask[py1:py2, px1:px2]
                                    red_pixels = cv2.countNonZero(box_mask)
                                    red_density = red_pixels / box_mask.size if box_mask.size > 0 else 0
                                    
                                    # 2. INNER-CENTER Check (To ignore rings like dartboards)
                                    bh, bw = box_mask.shape
                                    ch, cw = bh // 2, bw // 2
                                    ih, iw = int(bh * 0.4), int(bw * 0.4) # Inner height/width
                                    inner_mask = box_mask[ch-ih//2:ch+ih//2, cw-iw//2:cw+iw//2]
                                    inner_density = cv2.countNonZero(inner_mask) / inner_mask.size if inner_mask.size > 0 else 0

                                    # Accept if broad density is OK and INNER center is ALSO red
                                    if red_density > 0.12 and inner_density > 0.4:
                                        d["label"] = "ball" # Map to internal behavior key
                                        d["tier"] = "(AI)"
                                        processed_detections.append(d)
                                        ball_found = True
                                    else:
                                        # Skip non-red ball candidates
                                        pass
                                else:
                                    # If box dimensions are invalid, just skip this detection
                                    pass
                            else:
                                processed_detections.append(d) # Keep non-ball detections

                        # --- TIER 2: Refined Blob Fallback (Discovery) ---
                        if not ball_found and mask is not None:
                            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            sorted_cnts = sorted(contours, key=cv2.contourArea, reverse=True)[:3]
                            for cnt in sorted_cnts:
                                x, y, w, h = cv2.boundingRect(cnt)
                                if w < 18 or h < 18: continue 
                                
                                # High-precision validation for blobs
                                blob_mask = mask[y:y+h, x:x+w]
                                red_density = cv2.countNonZero(blob_mask) / blob_mask.size if blob_mask.size > 0 else 0
                                ch, cw = h // 2, w // 2
                                ih, iw = int(h * 0.4), int(w * 0.4) # Inner height/width
                                inner_mask = blob_mask[ch-ih//2:ch+ih//2, cw-iw//2:cw+iw//2]
                                inner_density = cv2.countNonZero(inner_mask) / inner_mask.size if inner_mask.size > 0 else 0
                                
                                # Solid check (ID > 0.5) ensures we catch the ball but ignore the dartboard ring
                                if red_density > 0.25 and inner_density > 0.55:
                                    processed_detections.append({
                                        "label": "ball",
                                        "score": 0.85,
                                        "box": [y/h_frame, x/w_frame, (y+h)/h_frame, (x+w)/w_frame],
                                        "tier": "(BLOB)"
                                    })
                                    ball_found = True
                                    break
                        
                        # Final loop for all validated detections
                        for d in processed_detections:
                            label = d["label"]
                            # Skip original AI labels for ball candidates, as they've been processed
                            if label in ["sports ball", "apple", "orange"]: continue
                            
                            if label in ["person", "dog", "cat", "ball"]:
                                # Estimate distance 
                                ymin, xmin, ymax, xmax = d["box"]
                                height = ymax - ymin
                                center_x = (xmin + xmax) / 2
                                center_y = (ymin + ymax) / 2
                                dist_est = int(1000 / height) if height > 0 else 2000
                                
                                # Movement Tracking logic
                                interest_level = "unknown"
                                if label == "dog" and label in last_positions:
                                    prev_x, prev_y, prev_t = last_positions[label]
                                    dx = center_x - prev_x
                                    dy = center_y - prev_y
                                    dt = now - prev_t
                                    if dt > 0:
                                        vel = np.sqrt(dx**2 + dy**2) / dt
                                        interest_level = "active" if vel > 0.1 else "calm"
                                
                                last_positions[label] = (center_x, center_y, now)

                                # --- TILT SERVO LOGIC (Queue-based) ---
                                if label in ["person", "dog"] and (time.time() - self.last_tilt_update > 0.5):
                                    target_tilt = 90
                                    if dist_est < 600: target_tilt = 60
                                    elif dist_est < 1200: target_tilt = 75
                                    elif dist_est > 1800: target_tilt = 85
                                    
                                    if target_tilt != self.tilt_angle:
                                        self.tilt_angle = target_tilt
                                        try:
                                            if self.result_queue.full():
                                                self.result_queue.get_nowait()
                                            self.result_queue.put_nowait({
                                                "type": "tilt_request",
                                                "angle": target_tilt
                                            })
                                            self.last_tilt_update = time.time()
                                        except Exception: pass
                                
                                # For ball, interest depends on distance/speed
                                if label == "ball":
                                    interest_level = "high"
                                    
                                # --- FACE RECOGNITION STEP ---
                                face_vec, face_jpg, face_rect = None, None, None
                                if label == "person":
                                    try:
                                        face_vec, face_jpg, face_rect = face_analyzer.analyze(frame, d["box"])
                                    except Exception: pass

                                try:
                                    final_cx, final_cy = center_x, center_y
                                    # If a face was found, use the face box for tighter visualization instead of the person box
                                    final_box = d["box"]
                                    if face_rect:
                                        final_box = face_rect
                                        # Re-calculate center for tracking
                                        ymin_f, xmin_f, ymax_f, xmax_f = face_rect
                                        center_x = (xmin_f + xmax_f) / 2
                                        center_y = (ymin_f + ymax_f) / 2

                                    if soft_stab and remap_params:
                                        # Transform normalized back to pixel, then stabilize, then back to normalized
                                        px, py = center_x * w_frame, center_y * h_frame
                                        sx, sy = self.transform_coords(px, py, *remap_params)
                                        final_cx, final_cy = sx / w_frame, sy / h_frame

                                    if self.result_queue.full():
                                        self.result_queue.get_nowait()
                                    
                                    res = {
                                        "type": "object", 
                                        "label": label, 
                                        "dist": dist_est,
                                        "score": d["score"],
                                        "interest": interest_level,
                                        "center_x": final_cx,
                                        "center_y": final_cy,
                                        "box": final_box, # Added tighter box to result
                                        "timestamp": time.time()
                                    }
                                    if face_vec:
                                        res["face_vec"] = face_vec
                                        if face_jpg:
                                            res["face_jpg"] = face_jpg
                                        
                                    self.result_queue.put_nowait(res)
                                except Exception: pass
                                
                                # Cache for visualization
                                color = (0, 255, 255) # Yellow for generic
                                current_label = label.upper()
                                if label == "ball":
                                    color = (0, 0, 255) # RED for the red ball
                                    tier_suffix = d.get("tier", "")
                                    current_label = f"BALL {tier_suffix}"
                                elif label == "person": 
                                    color = (255, 255, 255) # White for stranger
                                    if self.current_identity:
                                        color = (0, 255, 0) # Green for recognized
                                        current_label = self.current_identity.upper()
                                
                                # Use the tighter box (Face) if available
                                viz_box = face_rect if face_rect else d["box"]

                                viz_objects_new.append({
                                    "label": current_label,
                                    "dist": dist_est,
                                    "box": viz_box,
                                    "color": color
                                })
                            
                                icon = "👤" if label == "person" else ("⚽" if label == "ball" else "🐾")
                                interest_str = f" [Interest: {interest_level}]" if label in ["dog", "ball"] else ""
                                if frame_count % 50 == 0: # Even less frequent, and at DEBUG level
                                    logger.debug(f"Target Status: {label.upper()} {icon}{interest_str} (Conf: {d['score']:.2f}, Dist: {dist_est if 'dist_est' in locals() else 0}mm)")
                            
                        viz_state["objects"] = viz_objects_new

                    # --- STREAMING STEP: Send frame to Web Server ---
                    if self.frame_queue is not None:
                        # Update soft stab setting from shared flags if available
                        soft_stab = self.software_stab
                        if self.shared_flags:
                            soft_stab = bool(self.shared_flags[1])

                        # --- DIGITAL IMAGE STABILIZATION (DIS) ---
                        if soft_stab and self.shared_imu:
                            h, w = frame.shape[:2]
                            roll, pitch, yaw = self.shared_imu[0], self.shared_imu[1], self.shared_imu[2]
                            
                            # A. Rotation (Roll compensation)
                            center = (w // 2, h // 2)
                            M_rot = cv2.getRotationMatrix2D(center, -roll, 1.0)
                            
                            # B. Translation (Pitch/Yaw compensation)
                            # Heuristic mapping: Shift pixels based on angles assuming a 45° FOV.
                            # A 1-degree rotation results in roughly (width / FOV) pixels of movement.
                            # Opposite of yaw (side-to-side) and same as pitch (up-down) due to camera orientation.
                            shift_x = -yaw * (w / 45.0) 
                            shift_y = pitch * (h / 45.0) 
                            M_rot[0, 2] += shift_x
                            M_rot[1, 2] += shift_y
                            
                            # C. Apply Transformation & Crop
                            frame = cv2.warpAffine(frame, M_rot, (w, h), flags=cv2.INTER_LINEAR)
                            cw, ch = int(w * self.stab_crop), int(h * self.stab_crop)
                            frame = frame[ch:h-ch, cw:w-cw]
                            frame = cv2.resize(frame, (w, h))

                        # --- FINAL VISUALIZATION RENDERING (After Stabilization) ---
                        # Update show_debug setting from shared flags if available
                        show_debug = self.config.get("system.show_vision_debug", True)
                        if self.shared_flags:
                            show_debug = bool(self.shared_flags[0])
                        
                        h_draw, w_draw = frame.shape[:2]
                        
                        # Displacement parameters for coordinate remapping
                        remap_params = None
                        if soft_stab and self.shared_imu:
                            # scale factors for the resize back to (w, h)
                            sw = w / (w - 2*cw)
                            sh = h / (h - 2*ch)
                            remap_params = (M_rot, cw, ch, sw, sh)

                        if show_debug:
                            
                            # Draw Gesture
                            if viz_state["gesture"]:
                                g_label, g_time = viz_state["gesture"]
                                if time.time() - g_time < 2.0:
                                    cv2.putText(frame, f"GESTURE: {g_label}", (10, 30), 
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                                else:
                                    viz_state["gesture"] = None
                            
                            # Draw Landmarks (Aruco - New Overlay)
                            if viz_state["landmarks"]:
                                ids_v, corners_v = viz_state["landmarks"]
                                for i, marker_id in enumerate(ids_v.flatten()):
                                    marker_corners_2d = corners_v[i][0]
                                    pts = []
                                    for corner in marker_corners_2d:
                                        cx, cy = corner[0], corner[1]
                                        if remap_params:
                                            cx, cy = self.transform_coords(cx, cy, *remap_params)
                                        pts.append((int(cx), int(cy)))
                                    
                                    # Draw square
                                    for j in range(4):
                                        cv2.line(frame, pts[j], pts[(j+1)%4], (255, 191, 0), 2)
                                    
                                    # Draw ID
                                    cv2.putText(frame, f"ID:{marker_id}", (pts[0][0], pts[0][1]-10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 191, 0), 2)
                                    
                                    # Draw 3D Axes
                                    # hs already exists from detection block? No, it's not in scope here.
                                    # We need to re-calculate hs or pass it. 
                                    # Let's assume hs = phys_size/2.0
                                    m_id_str = str(marker_id)
                                    ps = 100.0
                                    if m_id_str in self.config.get("mapping.markers", {}):
                                        ps = self.config.get("mapping.markers", {})[m_id_str].get("size", 100.0)
                                    hs = ps / 2.0
                                    
                                    # Re-calculate rvec/tvec for drawing (usually it's faster to cache them, 
                                    # but we're in the viz block. Let's just draw 3 lines)
                                    # To draw axes, we needcam_matrix. 
                                    cam_matrix = np.array([[300, 0, 160],[0, 300, 120],[0, 0, 1]], dtype=np.float32)
                                    dist_coeffs = np.zeros((4,1))
                                    
                                    # Define axis points in 3D
                                    axis_len = hs * 1.5
                                    axis_pts_3d = np.array([
                                        [0, 0, 0],
                                        [axis_len, 0, 0],  # X
                                        [0, axis_len, 0],  # Y
                                        [0, 0, -axis_len]   # Z (pointing towards camera from marker)
                                    ], dtype=np.float32)
                                    
                                    # We need rvec and tvec from the detection step. 
                                    # Since they are not cached in viz_state, let's re-run PnP for the viz
                                    # Or better, I should have put them in a dict.
                                    # For now, let's just project a simple 3D axis if we have corners.
                                    obj_pts = np.array([[-hs, hs, 0],[hs, hs, 0],[hs, -hs, 0],[-hs, -hs, 0]], dtype=np.float32)
                                    success, r, t = cv2.solvePnP(obj_pts, corners[i][0].astype(np.float32), cam_matrix, dist_coeffs)
                                    if success:
                                        imgpts, _ = cv2.projectPoints(axis_pts_3d, r, t, cam_matrix, dist_coeffs)
                                        imgpts = imgpts.reshape(-1, 2)
                                        
                                        # Transform to stabilized frame
                                        pts_2d = []
                                        for pt in imgpts:
                                            px, py = pt[0], pt[1]
                                            if remap_params:
                                                px, py = self.transform_coords(px, py, *remap_params)
                                            pts_2d.append((int(px), int(py)))
                                        
                                        # Draw Axis lines: X=Red, Y=Green, Z=Blue
                                        origin = pts_2d[0]
                                        cv2.line(frame, origin, pts_2d[1], (0, 0, 255), 3) # X
                                        cv2.line(frame, origin, pts_2d[2], (0, 255, 0), 3) # Y
                                        cv2.line(frame, origin, pts_2d[3], (255, 0, 0), 3) # Z

                            # Draw Objects
                            for obj in viz_state["objects"]:
                                ymin, xmin, ymax, xmax = obj["box"]
                                # Convert normalized to pixel
                                left, top = xmin * w, ymin * h
                                right, bottom = xmax * w, ymax * h
                                
                                if remap_params:
                                    left, top = self.transform_coords(left, top, *remap_params)
                                    right, bottom = self.transform_coords(right, bottom, *remap_params)

                                cv2.rectangle(frame, (int(left), int(top)), (int(right), int(bottom)), obj["color"], 2)
                                
                                label_str = f"{obj['label']} {obj['dist']}mm"
                                if obj['label'] == 'PERSON' and self.current_identity:
                                    label_str = f"{self.current_identity.upper()} {obj['dist']}mm"
                                    
                                cv2.putText(frame, label_str, (int(left), int(top)-10), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, obj["color"], 2)
                                            
                            # Heartbeat indicator
                            if frame_count % 2 == 0:
                                cv2.circle(frame, (w_draw-10, 10), 3, (0, 255, 0), -1)
                        else:
                            # Always draw a small heartbeat even if debug is off, but make it subtler
                            if frame_count % 10 == 0:
                                cv2.circle(frame, (w_draw-5, 5), 1, (0, 150, 0), -1)

                        ret, buffer = cv2.imencode('.jpg', frame)
                        if ret:
                            # Atomic update: only keep the freshest frame
                            if self.frame_queue.full():
                                try: self.frame_queue.get_nowait()
                                except: pass
                            # Use put_nowait to avoid blocking the shutdown if the queue fills up
                            try:
                                self.frame_queue.put_nowait(buffer.tobytes())
                            except Exception: pass
                            if frame_count % 100 == 0:
                                logger.debug("Vision stream frame pushed to queue.")
                        else:
                            logger.warning("Failed to encode frame for streaming.")
                except Exception as e:
                    logger.error(f"Error in Vision loop body: {e}")

            # Control processing rate to avoid pinning CPU
            time.sleep(0.05) # ~20 FPS limit
            
        if cap:
            cap.release()
        logger.info("Vision process stopped")
