import multiprocessing
import time
import logging
import numpy as np
import os

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import mediapipe as mp
except ImportError:
    mp = None

# TFLite for Object Detection
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    try:
        import warnings
        # Suppress TensorFlow Lite deprecation warning
        warnings.filterwarnings("ignore", category=UserWarning, module="tensorflow.lite")
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
        Returns: (embedding, face_jpg_bytes) or (None, None)
        """
        if not self.detector or not self.recognizer or frame is None:
            return None, None
            
        try:
            h, w = frame.shape[:2]
            ymin, xmin, ymax, xmax = box
            left, top, right, bottom = int(xmin*w), int(ymin*h), int(xmax*w), int(ymax*h)
            
            # Crop person area with some padding
            pad = 20
            person_crop = frame[max(0, top-pad):min(h, bottom+pad), max(0, left-pad):min(w, right+pad)]
            if person_crop.size == 0 or person_crop.shape[0] < 10 or person_crop.shape[1] < 10:
                return None, None
                
            # Detect face in crop
            self.detector.setInputSize((person_crop.shape[1], person_crop.shape[0]))
            _, faces = self.detector.detect(person_crop)
            
            if faces is not None and len(faces) > 0:
                # Take the largest face (SFace requires input image to be 3-channel BGR)
                face = faces[0]
                # Align and recognize
                aligned = self.recognizer.alignCrop(person_crop, face)
                if aligned is not None and aligned.size > 0:
                    feature = self.recognizer.feature(aligned)
                    
                    # Encode a slightly larger crop for the dashboard (not just the aligned face)
                    # We use the 'aligned' image as it's already normalized and centered
                    _, buffer = cv2.imencode('.jpg', aligned)
                    return feature.flatten().tolist(), buffer.tobytes()
        except Exception as e:
            logger.debug(f"FaceAnalyzer error: {e}")
            
        return None, None

class VisionProcess(multiprocessing.Process):
    def __init__(self, result_queue: multiprocessing.Queue, frame_queue: multiprocessing.Queue, config, shared_imu=None, identity_queue=None):
        """
        Runs in a separate process to avoid blocking the high-frequency motor control loop.
        :param result_queue: Queue to send detection results back to the brain.
        :param frame_queue: Queue to send raw frames to the web server for streaming.
        :param identity_queue: Queue to receive recognized names from the brain.
        """
        super().__init__()
        self.result_queue = result_queue
        self.frame_queue = frame_queue
        self.identity_queue = identity_queue
        self.config = config
        self.running = multiprocessing.Event()
        self.current_identity = None # Local cache of the recognized person name
        
        # Load Camera Tilt Config
        camera_cfg = self.config.get("servos.camera.tilt", {})
        self.tilt_channel = camera_cfg.get("channel", 14)
        self.tilt_angle = camera_cfg.get("middle", 90)
        self.tilt_min = camera_cfg.get("min", 45)
        self.tilt_max = camera_cfg.get("max", 135)
        self.shared_imu = shared_imu
        self.mechanical_stab = self.config.get("system.camera_stabilization", True)
        self.software_stab = self.config.get("system.software_stabilization", True)
        self.stab_crop = self.config.get("system.stabilization_crop", 0.15) # 15% crop for DIS
        self.last_tilt_update = time.time()

    def stop(self):
        self.running.clear()

    def run(self):
        self.running.set()
        logger.info("Vision process started (Real AI Mode)")
        
        # 1. Initialize AI Models
        # MediaPipe for Gestures
        hands = None
        if mp is not None:
            mp_hands = mp.solutions.hands
            hands = mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )

        # TFLite for Object Detection (Person/Pet)
        detector = None
        model_path = "brain/models/coco_ssd_mobilenet.tflite"
        label_path = "brain/models/labelmap.txt"
        try:
            detector = ObjectDetector(model_path, label_path)
            logger.info("TFLite Object Detector loaded successfully.")
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
            "objects": []    # List of (label, dist, box, color)
        }
        
        # --- FACE ANALYZER ---
        face_detector_path = os.path.join(os.path.dirname(__file__), "models", "face_detection_yunet.onnx")
        face_recognizer_path = os.path.join(os.path.dirname(__file__), "models", "face_recognition_sface.onnx")
        face_analyzer = FaceAnalyzer(face_detector_path, face_recognizer_path)

        while self.running.is_set():
            frame_count += 1
            if frame_count % 200 == 0:
                logger.info(f"Vision capture loop active (Frame: {frame_count})")
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
                    # --- AI STEP 0: AI Throttling ---
                    do_ai = (frame_count % processing_skip == 0)
                    
                    if do_ai:
                        # --- AI STEP 0: Red Ball Detection (HSV Filter) ---
                        # Red has two ranges in HSV (0-10 and 170-180)
                        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                        mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
                        mask2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
                        mask = cv2.add(mask1, mask2)
                    
                        # Morphological operations to clean up noise
                        mask = cv2.erode(mask, None, iterations=2)
                        mask = cv2.dilate(mask, None, iterations=2)
                        
                        # Find contours
                        cnts, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if len(cnts) > 0:
                            c = max(cnts, key=cv2.contourArea)
                            ((x, y), radius) = cv2.minEnclosingCircle(c)
                            if radius > 10: # Minimum size
                                # Normalize coordinates
                                h_frame, w_frame = frame.shape[:2]
                                try:
                                    if self.result_queue.full():
                                        self.result_queue.get_nowait()
                                    self.result_queue.put_nowait({
                                        "type": "object",
                                        "label": "ball",
                                        "dist": int(2000 / radius) if radius > 0 else 2000, # Heuristic
                                        "center_x": x / w_frame,
                                        "center_y": y / h_frame,
                                        "conf": 0.9,
                                        "interest": "high"
                                    })
                                except Exception: pass
                                
                                # Cache for visualization
                                viz_state["ball"] = (x, y, radius)
                            else:
                                viz_state["ball"] = None
                        else:
                            viz_state["ball"] = None

                    # --- AI STEP 1: Gesture Recognition (MediaPipe) ---
                    if do_ai and hands is not None:
                        # MediaPipe needs RGB
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        results = hands.process(rgb_frame)
                        
                        if results.multi_hand_landmarks:
                            for hand_landmarks in results.multi_hand_landmarks:
                                # 1. Count fingers (Very simplified logic)
                                # Index of finger tips: 4, 8, 12, 16, 20
                                # We check if tip is above its lower joint
                                fingers = []
                                # Thumb (landmark 4 vs 2 for horizontal/vertical) 
                                # This depends on orientation, but let's stick to easy ones
                                for tip_id in [8, 12, 16, 20]:
                                    if hand_landmarks.landmark[tip_id].y < hand_landmarks.landmark[tip_id - 2].y:
                                        fingers.append(1)
                                
                                count = sum(fingers)
                                label = None 
                                if count >= 4:
                                    label = "COME" # Open hand (4-5 fingers)
                                elif count == 2:
                                    label = "SIT" # Peace sign
                                elif count == 1:
                                    label = "DOWN" # Pointing finger
                                elif count == 0:
                                    label = "AWAY" # Closed fist
                                
                                if label:
                                    try:
                                        if self.result_queue.full():
                                            self.result_queue.get_nowait()
                                        self.result_queue.put_nowait({
                                            "type": "gesture",
                                            "label": label,
                                            "confidence": 0.95
                                        })
                                    except Exception: pass
                                    
                                    # Cache for visualization
                                    if label:
                                        viz_state["gesture"] = (label, time.time())

                    # --- AI STEP 2: Object Detection (TFLite) ---
                    if do_ai and detector is not None:
                        detections = detector.detect(frame)
                        now = time.time()
                        viz_objects_new = [] # Fix: Initialize before loop
                        for d in detections:
                            label = d["label"]
                            if label in ["person", "dog", "cat"]:
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
                                    
                                    # If dog is moving away (increasing x or moving out of frame side)
                                    # or if height is decreasing significantly
                                    if dt > 0:
                                        # Very simple: if moving laterally fast or shrinking
                                        if abs(dx) > 0.1 or (dy > 0.05): # simplified heuristic
                                            interest_level = "low"
                                        else:
                                            interest_level = "high"
                                
                                last_positions[label] = (center_x, center_y, now)

                                # --- TILT SERVO LOGIC (Queue-based) ---
                                # Adjust camera tilt based on distance if it's a priority object
                                if label in ["person", "dog"] and (time.time() - self.last_tilt_update > 0.5):
                                    # Corrected Mapping for tracking a taller object from a low robot:
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
                                         
                                # --- FACE RECOGNITION STEP ---
                                face_vec, face_jpg = None, None
                                if label == "person":
                                    try:
                                        face_vec, face_jpg = face_analyzer.analyze(frame, d["box"])
                                    except Exception: pass

                                try:
                                    if self.result_queue.full():
                                        self.result_queue.get_nowait()
                                    
                                    res = {
                                        "type": "object", 
                                        "label": label, 
                                        "dist": dist_est,
                                        "score": d["score"],
                                        "interest": interest_level,
                                        "center_x": center_x,
                                        "center_y": center_y,
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
                                if label == "person": color = (255, 0, 0) # Blue
                                elif label == "dog": color = (0, 165, 255) # Orange
                                
                                viz_objects_new.append({
                                    "label": label.upper(),
                                    "dist": dist_est,
                                    "box": d["box"],
                                    "color": color
                                })
                                
                                icon = "👤" if label == "person" else "🐾"
                                interest_str = f" [Interest: {interest_level}]" if label == "dog" else ""
                                logger.info(f"Target Acquired: {label.upper()} {icon}{interest_str} (Conf: {d['score']:.2f}, Dist: {dist_est}mm)")
                            
                        viz_state["objects"] = viz_objects_new

                    # --- STREAMING STEP: Send frame to Web Server ---
                    if self.frame_queue is not None:
                        # --- DIGITAL IMAGE STABILIZATION (DIS) ---
                        if self.software_stab and self.shared_imu:
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
                        show_debug = self.config.get("system.show_vision_debug", True)
                        h_draw, w_draw = frame.shape[:2]
                        
                        if show_debug:
                            # Draw Ball
                            if viz_state["ball"]:
                                bx, by, br = viz_state["ball"]
                                cv2.circle(frame, (int(bx), int(by)), int(br), (0, 255, 0), 2)
                                cv2.putText(frame, "Ball", (int(bx)-20, int(by)-int(br)-10), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            
                            # Draw Gesture
                            if viz_state["gesture"]:
                                g_label, g_time = viz_state["gesture"]
                                if time.time() - g_time < 2.0:
                                    cv2.putText(frame, f"GESTURE: {g_label}", (10, 30), 
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                                else:
                                    viz_state["gesture"] = None
                            
                            # Draw Objects
                            for obj in viz_state["objects"]:
                                ymin, xmin, ymax, xmax = obj["box"]
                                left, top = int(xmin * w_draw), int(ymin * h_draw)
                                right, bottom = int(xmax * w_draw), int(ymax * h_draw)
                                cv2.rectangle(frame, (left, top), (right, bottom), obj["color"], 2)
                                
                                # Use recognized identity if it's a person and we have one
                                display_label = obj["label"]
                                if obj["label"] == "PERSON" and self.current_identity:
                                    display_label = self.current_identity.upper()
                                    
                                label_str = f"{display_label} {obj['dist']}mm"
                                cv2.putText(frame, label_str, (left, top-10), 
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
                            self.frame_queue.put(buffer.tobytes())
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
