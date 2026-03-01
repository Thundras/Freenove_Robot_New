import multiprocessing
import time
import logging
import numpy as np

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

class VisionProcess(multiprocessing.Process):
    def __init__(self, result_queue: multiprocessing.Queue, frame_queue: multiprocessing.Queue, config, shared_imu=None):
        """
        Runs in a separate process to avoid blocking the high-frequency motor control loop.
        :param result_queue: Queue to send detection results back to the brain.
        :param frame_queue: Queue to send raw frames to the web server for streaming.
        """
        super().__init__()
        self.result_queue = result_queue
        self.frame_queue = frame_queue
        self.config = config
        self.running = multiprocessing.Event()
        
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
        
        while self.running.is_set():
            frame_count += 1
            frame = None
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

            if frame is not None:
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
                                self.result_queue.put_nowait({
                                    "type": "object",
                                    "label": "ball",
                                    "dist": int(2000 / radius) if radius > 0 else 2000, # Heuristic
                                    "center_x": x / w_frame,
                                    "center_y": y / h_frame,
                                    "conf": 0.9,
                                    "interest": "high"
                                })
                            except: pass

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
                            label = "AWAY" # Default/Stop
                            if count >= 3:
                                label = "COME" # Open hand
                            elif count == 2:
                                label = "SIT" # Peace sign
                            elif count == 1:
                                label = "DOWN" # Pointing finger / Down command
                            
                            try:
                                self.result_queue.put_nowait({
                                    "type": "gesture",
                                    "label": label,
                                    "confidence": 0.95
                                })
                            except: pass

                # --- AI STEP 2: Object Detection (TFLite) ---
                if do_ai and detector is not None:
                    detections = detector.detect(frame)
                    now = time.time()
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
                                        self.result_queue.put_nowait({
                                            "type": "tilt_request",
                                            "angle": self.tilt_angle
                                        })
                                    except: pass
                                    self.last_tilt_update = time.time()

                            try:
                                self.result_queue.put_nowait({
                                    "type": "object", 
                                    "label": label, 
                                    "dist": dist_est,
                                    "score": d["score"],
                                    "interest": interest_level,
                                    "center_x": center_x,
                                    "center_y": center_y
                                })
                            except: pass
                            
                            icon = "👤" if label == "person" else "🐾"
                            interest_str = f" [Interest: {interest_level}]" if label == "dog" else ""
                            logger.info(f"Target Acquired: {label.upper()} {icon}{interest_str} (Conf: {d['score']:.2f}, Dist: {dist_est}mm)")

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

                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        # Atomic update: only keep the freshest frame
                        if self.frame_queue.full():
                            try: self.frame_queue.get_nowait()
                            except: pass
                        self.frame_queue.put(buffer.tobytes())

            # Control processing rate to avoid pinning CPU
            time.sleep(0.05) # ~20 FPS limit
            
        if cap:
            cap.release()
        logger.info("Vision process stopped")
