import logging
import multiprocessing
import time
import json
import os
import numpy as np
from .bt_core import Selector, Sequence
from .behaviors import AvoidObstacles, SmartExplore, ReactToPerson, FollowPerson, Idle, HandleGesture, AlarmPulse, SecurityMonitor, DogSocialInteraction, PlayWithBall, AmbientLook, ReactToFace
from .vision import VisionProcess

logger = logging.getLogger(__name__)

class SocialMemory:
    """
    Manages face database, trust scores, and multi-view templates.
    Supports persistent storage of face embeddings and captured images.
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self.faces = {} # face_id -> {embedding, exposure, last_seen, name}
        self.load()

    def load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    # Migration: convert single embedding to list
                    for fid, f_data in data.items():
                        if "embedding" in f_data:
                            f_data["embeddings"] = [f_data["embedding"]]
                            del f_data["embedding"]
                    self.faces = data
            except Exception as e:
                logger.error(f"Failed to load face DB: {e}")

    def save(self):
        try:
            with open(self.db_path, 'w') as f:
                json.dump(self.faces, f)
        except Exception as e:
            logger.error(f"Failed to save face DB: {e}")

    def match_face(self, vec):
        """
        Finds the closest face matching the input vector using multi-view templates.
        Compares input against all stored viewpoints for every person.
        If a person is recognized but from a significantly new angle, adds it as a new template.
        Returns: (face_id, distance) or (new_face_id, 0.0)
        """
        if not vec: return None, 0.0
        
        vec = np.array(vec)
        if vec.size == 0: return None, 0.0
        
        # Normalize incoming vector for stability
        vec = vec / (np.linalg.norm(vec) + 1e-6)
        
        # SFace L2 distance threshold: 1.12 recommended.
        # With normalization, 1.0 is a solid "strong match" threshold.
        match_threshold = 1.0 
        new_angle_threshold = 0.5 # Distance at which we add a NEW template for an EXISTING person
        
        best_id = None
        min_dist = match_threshold
        
        for fid, data in self.faces.items():
            # Check against ALL stored embeddings for this person
            for db_vec_list in data.get("embeddings", []):
                db_vec = np.array(db_vec_list)
                db_vec = db_vec / (np.linalg.norm(db_vec) + 1e-6) # Ensure normalized
                
                dist = np.linalg.norm(vec - db_vec)
                if dist < min_dist:
                    min_dist = dist
                    best_id = fid
                
        if best_id:
            # Gradually update the stored embedding to follow aging/lighting
            # We update the *closest* matched embedding
            data = self.faces[best_id]
            
            # Check if this view is significantly new (e.g. turned head)
            # If it matched reasonably well but is still far from existing views, add it
            is_new_angle = True
            for db_vec_list in data["embeddings"]:
                if np.linalg.norm(vec - np.array(db_vec_list)) < new_angle_threshold:
                    is_new_angle = False
                    break
            
            if is_new_angle and len(data["embeddings"]) < 10:
                logger.info(f"Learned new viewpoint for {best_id}")
                data["embeddings"].append(vec.tolist())
            else:
                # Update existing (closest) embedding slightly
                alpha = 0.01 
                # Re-find index of closest one for updating
                best_idx = 0
                idx_min = 2.0
                for i, v in enumerate(data["embeddings"]):
                    d = np.linalg.norm(vec - np.array(v))
                    if d < idx_min:
                        idx_min = d
                        best_idx = i
                
                old_v = np.array(data["embeddings"][best_idx])
                data["embeddings"][best_idx] = (old_v * (1-alpha) + vec * alpha).tolist()
                
            return best_id, min_dist
        
        # Create new unknown persona
        new_id = f"Person_{int(time.time()) % 10000}_{len(self.faces)}"
        self.faces[new_id] = {
            "embeddings": [vec.tolist()],
            "exposure": 0.0,
            "last_seen": time.time(),
            "name": f"New Stranger {len(self.faces)}"
        }
        return new_id, 0.0

    def update_exposure(self, face_id, dt):
        if face_id in self.faces:
            self.faces[face_id]["exposure"] += dt
            self.faces[face_id]["last_seen"] = time.time()
            # Cubic trust curve: trust = (hours / 1)^3 
            # or (seconds / 3600)^3
            exposure = self.faces[face_id]["exposure"]
            trust = min(1.0, (exposure / 3600.0)**3)
            return trust
        return 0.0

    def save_face_image(self, face_id, jpg_bytes):
        """Saves face crop to static directory for dashboard"""
        if not jpg_bytes: return
        
        # Save to api/static/faces/ (relative to workspace root)
        # Note: IntelligenceController is in brain/
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "static", "faces")
        if not os.path.exists(static_dir):
            os.makedirs(static_dir, exist_ok=True)
            
        file_path = os.path.join(static_dir, f"{face_id}.jpg")
        try:
            with open(file_path, 'wb') as f:
                f.write(jpg_bytes)
        except Exception as e:
            logger.error(f"Failed to save face image {face_id}: {e}")

    def cleanup_stale_faces(self, max_age_hours=2, min_exposure_seconds=15):
        """Deletes transient faces (0% trust) that haven't been seen for X hours"""
        now = time.time()
        to_delete = []
        
        for fid, data in self.faces.items():
            age = now - data.get("last_seen", 0)
            exposure = data.get("exposure", 0)
            
            # If exposure is very low (transient/noise) AND haven't seen for hours
            if exposure < min_exposure_seconds and age > (max_age_hours * 3600):
                to_delete.append(fid)
                
        if to_delete:
            logger.info(f"Cleaning up {len(to_delete)} transient faces from memory.")
            static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "static", "faces")
            for fid in to_delete:
                del self.faces[fid]
                # Also delete image
                img_path = os.path.join(static_dir, f"{fid}.jpg")
                if os.path.exists(img_path):
                    try: os.remove(img_path)
                    except: pass
            self.save()

class IntelligenceController:
    """
    Manages the robot's higher-level behavior tree and asynchronous vision pipeline.
    
    Context Injection: 
    Injects a shared 'context' dictionary into all Leaf nodes of the behavior tree.
    This context is used to share sensor data, detection results, and system state 
    globally between behaviors.
    """
    def __init__(self, config, sensors=None, gait=None, servo_ctrl=None):
        self.config = config
        self.sensors = sensors
        self.gait = gait
        self.servo_ctrl = servo_ctrl
        
        # State & Context for behaviors
        self.context = {
            "gait": gait,
            "sensors": self.sensors,
            "last_object_detection": None,
            "last_face": None, # face_id, trust_score
            "last_gesture": None,
            "system_mode": "autonomous", # autonomous, manual, sit, down
            "target_tilt": 90,
            "play_interest": 1.0 # Initial: Fully motivated
        }
        
        db_path = os.path.join(os.path.dirname(__file__), "face_db.json")
        self.social_memory = SocialMemory(db_path)
        self.last_db_save = time.time()
        
        # Vision Process for AI (Offloaded)
        # Use maxsize to prevent memory bloat and blockages if consumer (WebServer) stops
        self.result_queue = multiprocessing.Queue(maxsize=10)
        self.frame_queue = multiprocessing.Queue(maxsize=2)
        self.identity_queue = multiprocessing.Queue(maxsize=1) # Only latest identity
        self.shared_imu = multiprocessing.Array('d', [0.0, 0.0, 0.0]) # [Roll, Pitch, Yaw]
        
        self.vision = VisionProcess(
            self.result_queue, 
            self.frame_queue, 
            config, 
            shared_imu=self.shared_imu,
            identity_queue=self.identity_queue
        )
        
        # Stabilization state
        self.tilt_angle = config.get("servos.camera.tilt.middle", 90)
        self.tilt_channel = config.get("servos.camera.tilt.channel", 14)
        self.mech_stab_enabled = config.get("system.camera_stabilization", True)
        
        # BT Setup
        self.root = self.setup_behavior_tree()

    def setup_behavior_tree(self):
        """Construct the robot's main behavior tree"""
        # Node instances
        # Inject self into sensors for behaviors that need mode access (like AvoidObstacles)
        self.sensors["intelligence"] = self
        avoid = AvoidObstacles("AvoidObstacles", self.sensors)
        gesture = HandleGesture("HandleGesture", self.context)
        react_face = ReactToFace("ReactToFace", self.context)
        react = ReactToPerson("ReactToPerson", self.context)
        follow = FollowPerson("FollowPerson", self.context)
        social = DogSocialInteraction("DogSocialInteraction", self.context)
        ball = PlayWithBall("PlayWithBall", self.context)
        explore = SmartExplore("SmartExplore", self.gait, self.context)
        ambient = AmbientLook("AmbientLook", self.context)
        idle = Idle("IdleAnimation", self.gait)
        
        # Security Nodes
        security_alert = AlarmPulse("AlarmPulse", self.context)
        security_monitor = SecurityMonitor("SecurityMonitor", self.context)
        
        # Branches
        # Alarm Branch: Only triggers if system_mode is 'alarm' AND person detected
        alarm_branch = Sequence("AlarmBranch", [security_monitor, security_alert])
        
        # Interaction Branch
        interaction = Selector("InteractionBranch", [follow, react])
        
        # 1. Safety (Avoid)
        # 2. Alarm (Priority threat)
        # 3. Command (Gestures)
        # 4. Ball (Play)
        # 5. Social (Artgenossen)
        # 6. Social (Interaction/Person)
        # 6. Social (Interaction/Person)
        root = Selector("MainBrain", [avoid, alarm_branch, gesture, react_face, ball, social, interaction, explore, ambient, idle])
        return root

    def start(self):
        self.vision.start()
        logger.info("Intelligence controller started")

    def update(self):
        """Standard update loop (called from main)"""
        now = time.time()
        
        while not self.result_queue.empty():
            data = self.result_queue.get()
            data["timestamp"] = now # Local arrival time
            if data.get("type") == "object":
                # --- EMA SMOOTHING ---
                alpha = 0.4 # Smoothing factor (0.0 to 1.0)
                last = self.context.get("last_object_detection")
                if last and last["label"] == data["label"]:
                    data["center_x"] = last["center_x"] * (1 - alpha) + data["center_x"] * alpha
                    data["center_y"] = last["center_y"] * (1 - alpha) + data["center_y"] * alpha
                # --- FACE RECOGNITION ---
                if "face_vec" in data:
                    fid, dist = self.social_memory.match_face(data["face_vec"])
                    trust = self.social_memory.update_exposure(fid, 0.5) # Assuming ~2FPS
                    self.context["last_face"] = {"id": fid, "trust": trust, "timestamp": now}
                    
                    # Store/Update face image
                    # Update if new person (exposure < 10s) or if trust is still building
                    if data.get("face_jpg"):
                        if self.social_memory.faces[fid]["exposure"] < 10.0 or trust < 0.5:
                            self.social_memory.save_face_image(fid, data["face_jpg"])

                    # Feedback recognized name to vision overlay
                    display_name = self.social_memory.faces[fid].get("name", fid)
                    try:
                        if self.identity_queue.full():
                            self.identity_queue.get_nowait()
                        self.identity_queue.put_nowait(display_name)
                    except: pass

                    logger.debug(f"Face recognized: {fid} (Trust: {trust:.2f})")
                    
                    # Save DB periodically (every 30s)
                    if now - self.last_db_save > 30.0:
                        self.social_memory.cleanup_stale_faces() # Garbage collect transient detections
                        self.social_memory.save()
                        self.last_db_save = now
                
                self.context["last_object_detection"] = data
            elif data.get("type") == "gesture":
                self.context["last_gesture"] = data
            elif data.get("type") == "tilt_request":
                self.context["target_tilt"] = data.get("angle", 90)
        
        # Cleanup stale detections (older than 1.0s)
        if self.context["last_object_detection"] and (now - self.context["last_object_detection"].get("timestamp", 0) > 1.0):
             self.context["last_object_detection"] = None
        if self.context["last_gesture"] and (now - self.context["last_gesture"].get("timestamp", 0) > 0.5):
             self.context["last_gesture"] = None
        if self.context["last_face"] and (now - self.context["last_face"].get("timestamp", 0) > 1.0):
             self.context["last_face"] = None
             # Clear identity in vision if lost
             try:
                 if self.identity_queue.full():
                     self.identity_queue.get_nowait()
                 self.identity_queue.put_nowait(None)
             except: pass
        
        # Mode Change Detection & Logging
        current_mode = self.context.get("system_mode")
        if not hasattr(self, "_last_mode_logged") or self._last_mode_logged != current_mode:
            logger.info(f"!!! SYSTEM MODE CHANGE: {getattr(self, '_last_mode_logged', 'init')} -> {current_mode} !!!")
            self._last_mode_logged = current_mode
            
        # Periodic Status Heartbeat (every 5 seconds)
        if int(now) % 5 == 0:
            if not hasattr(self, "_last_heartbeat_tick") or self._last_heartbeat_tick != int(now):
                logger.info(f"[HEARTBEAT] Mode: {current_mode} | Object: {'Yes' if self.context['last_object_detection'] else 'No'}")
                self._last_heartbeat_tick = int(now)
        
        # Update shared IMU data for vision stabilization (Roll, Pitch, Yaw)
        if self.sensors and "imu" in self.sensors:
            imu_data = self.sensors["imu"].get_data()
            if imu_data:
                self.shared_imu[0] = imu_data.roll
                self.shared_imu[1] = imu_data.pitch
                self.shared_imu[2] = imu_data.yaw
                
                # Apply Mechanical Stabilization (100Hz sync)
                if self.servo_ctrl and self.mech_stab_enabled:
                    # Apply inversion
                    pitch_error = imu_data.pitch
                    if self.config.get("servos.camera.tilt.inverted", False):
                        pitch_error = -pitch_error
                    
                    # target_angle = base_tilt - body_pitch
                    target_tilt = self.context.get("target_tilt", 90)
                    stab_angle = target_tilt - pitch_error
                    # Clamp to safe limits
                    min_a = self.config.get("servos.camera.tilt.min", 45)
                    max_a = self.config.get("servos.camera.tilt.max", 135)
                    stab_angle = max(min_a, min(max_a, stab_angle))
                    
                    self.servo_ctrl.set_angle(self.tilt_channel, stab_angle)
        
        # Execute Behavior Tree
        self.root.run()

    def stop(self):
        logger.info("Stopping Intelligence controller (Vision Process)...")
        self.vision.stop()
        # Wait for graceful stop with timeout, then force if needed
        self.vision.join(timeout=2.0)
        if self.vision.is_alive():
            logger.warning("Vision process did not stop gracefully, terminating.")
            self.vision.terminate()
        logger.info("Intelligence controller stopped")
