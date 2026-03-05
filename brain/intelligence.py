import logging
import multiprocessing
import time
import json
import os
import numpy as np
from .bt_core import Selector, Sequence, Parallel
from .behaviors import AvoidObstacles, SmartExplore, ReactToPerson, FollowPerson, Idle, HandleGesture, AlarmPulse, SecurityMonitor, DogSocialInteraction, PlayWithBall, AmbientLook, ReactToFace, ExpressMood
from .vision import VisionProcess
from .mapping import MappingManager
from .mood import MoodManager

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

    def update_exposure(self, face_id, dt, now_ts=None):
        if face_id in self.faces:
            self.faces[face_id]["exposure"] += dt
            self.faces[face_id]["last_seen"] = now_ts or time.time()
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

    def rename_face(self, face_id, new_name):
        if face_id in self.faces:
            self.faces[face_id]["name"] = new_name
            self.save()
            logger.info(f"Face {face_id} renamed to '{new_name}'")
            return True
        return False

    def delete_face(self, face_id):
        if face_id in self.faces:
            del self.faces[face_id]
            # Also delete image
            static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "static", "faces")
            img_path = os.path.join(static_dir, f"{face_id}.jpg")
            if os.path.exists(img_path):
                try: os.remove(img_path)
                except: pass
            self.save()
            logger.info(f"Face {face_id} deleted from memory.")
            return True
        return False

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
            "play_interest": 1.0, # Initial: Fully motivated
            "gesture_trust_threshold": config.get("system.gesture_trust_threshold", 0.1),
            "mood": MoodManager()
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
        self.shared_flags = multiprocessing.Array('i', [0] * 10) # [show_debug, soft_stab, ...]
        
        # Initialize flags from config
        self.shared_flags[0] = 1 if config.get("system.show_vision_debug", True) else 0
        self.shared_flags[1] = 1 if config.get("system.camera_stabilization", True) else 0

        self.vision = VisionProcess(
            self.result_queue, 
            self.frame_queue, 
            config, 
            shared_imu=self.shared_imu,
            identity_queue=self.identity_queue,
            shared_flags=self.shared_flags
        )
        
        # Stabilization state
        self.tilt_angle = config.get("servos.camera.tilt.middle", 90)
        self.tilt_channel = config.get("servos.camera.tilt.channel", 14)
        self.mech_stab_enabled = config.get("system.camera_stabilization", True)
        
        # SLAM / Mapping
        self.mapping = MappingManager()
        self.last_update_ts = time.time()
        
        # BT Setup
        self.root = self.setup_behavior_tree()

    def setup_behavior_tree(self):
        """Construct the robot's main behavior tree"""
        # Node instances
        self.sensors["intelligence"] = self
        
        # 1. Safety & System (Highest Priority)
        avoid = AvoidObstacles("AvoidObstacles", self.sensors)
        gesture = HandleGesture("HandleGesture", self.context)
        
        # 2. Emotional/Biological Layer (Parallel)
        # This node always runs to update body language, but returns success to let others continue
        express = ExpressMood("ExpressMood", self.context)
        
        # 3. Reactive Behaviors
        react_face = ReactToFace("ReactToFace", self.context)
        react_person = ReactToPerson("ReactToPerson", self.context)
        ball = PlayWithBall("PlayWithBall", self.context)
        social = DogSocialInteraction("DogSocialInteraction", self.context)
        
        # 4. Long-term Task / Explore
        follow = FollowPerson("FollowPerson", self.context)
        explore = SmartExplore("SmartExplore", self.gait, self.context)
        ambient = AmbientLook("AmbientLook", self.context)
        idle = Idle("IdleAnimation", self.gait)
        
        # Security Nodes
        security_alert = AlarmPulse("AlarmPulse", self.context)
        security_monitor = SecurityMonitor("SecurityMonitor", self.context)
        alarm_branch = Sequence("AlarmBranch", [security_monitor, security_alert])
        
        # --- TREE HIERARCHY ---
        
        # Interaction Selector: Priority of who/what to interact with
        interaction = Selector("InteractionBranch", [
            follow,         # explicit follow mode
            react_face,     # recognize friends/strangers
            react_person,   # general person detection
            ball,           # play with ball
            social          # dog social
        ])
        
        # Main Active Branch: Decisions about movement/tasks
        active_logic = Selector("ActiveLogic", [
            avoid, 
            alarm_branch, 
            gesture, 
            interaction, 
            explore, 
            ambient, 
            idle
        ])
        
        # The ROOT is a Parallel node:
        # It runs ExpressMood (Layer 1) ALWAYS, and ActiveLogic (Layer 2)
        # It succeeds if ActiveLogic succeeds (ExpressMood always succeeds)
        root = Parallel("MoodBrain", [express, active_logic], success_threshold=1)
        
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
                    
                    # Calculate actual dt based on vision timestamp
                    ts = data.get("timestamp", now)
                    last_seen = self.social_memory.faces[fid].get("last_seen", ts)
                    actual_dt = ts - last_seen
                    
                    # Cap dt: If person was gone > 1s, just add a tiny 0.05s starting increment
                    # Otherwise use real delta, capped to 0.5s max per frame pair
                    if actual_dt > 1.0 or actual_dt < 0:
                        actual_dt = 0.05
                    else:
                        actual_dt = min(actual_dt, 0.5)
                        
                    trust = self.social_memory.update_exposure(fid, actual_dt, now_ts=ts)
                    self.context["last_face"] = {"id": fid, "trust": trust, "timestamp": ts}
                    
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
            elif data.get("type") == "landmark":
                self.mapping.add_landmark(
                    data["id"], 
                    data["dist"], 
                    data["angle"],
                    data.get("marker_yaw", 0.0)
                )
            elif data.get("type") == "gesture":
                self.context["last_gesture"] = data
            elif data.get("type") == "tilt_request":
                self.context["target_tilt"] = data.get("angle", 90)
        
        # --- SLAM: Odometry update ---
        # --- MOOD: Update emotional states ---
        dt = now - self.last_update_ts
        self.context["mood"].update(dt)
        self.last_update_ts = now
        
        if self.gait:
            # step_length = 40mm per half-cycle = 80mm per full cycle? 
            # In update, speed is cyc/sec. 
            # Based on gait.py, speed of 1.0 means 1 full cycle (0 to 1.0 phase) per second.
            # During one cycle,stance phase covers 'step_length'.
            speed_mm_s = self.gait.current_speed * self.gait.step_length
            dx = speed_mm_s * dt
            # Estimation: turn_rate 1.0 -> ~0.8 rad/s (~45 deg/s)
            dyaw = self.gait.turn_rate * 0.8 * dt
            self.mapping.update_odometry(dx, 0.0, dyaw)
            
        # --- SLAM: Obstacle update ---
        if self.sensors and "ultrasonic" in self.sensors:
            u_data = self.sensors["ultrasonic"].get_data()
            if u_data:
                dist_cm = u_data.metadata.get("distance_cm", 100.0)
                dist_mm = dist_cm * 10
                
                # If we see an obstacle within 100cm, add it
                if dist_cm < 100.0:
                    self.mapping.add_obstacle(dist_mm, 0.0)
                    
                # If path is clear (e.g. > 20cm), clear points in front of us
                if dist_cm > 20.0:
                    # Clear up to the measured distance (capped at 1000mm)
                    self.mapping.clear_path(min(dist_mm, 1000.0), 0.0)
                
        # --- Sync Config to Vision Flags ---
        # Sync every tick (cheap) to ensure UI feels responsive
        self.shared_flags[0] = 1 if self.config.get("system.show_vision_debug", True) else 0
        self.shared_flags[1] = 1 if self.config.get("system.camera_stabilization", True) else 0
        
        # --- SLAM: Map Aging/Cleanup (Every 10 seconds) ---
        if now - getattr(self, "last_map_cleanup", 0) > 10.0:
            self.mapping.cleanup_old_points(max_age_seconds=300) # 5 min persistence
            self.last_map_cleanup = now
            
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
        
        # --- Social Memory: Periodic Cleanup (Every hour) ---
        if now - getattr(self, "last_memory_cleanup", 0) > 3600.0:
            max_age = self.config.get("system.social_memory_max_age_hours", 2)
            min_exp = self.config.get("system.social_memory_min_exposure", 60)
            self.social_memory.cleanup_stale_faces(max_age_hours=max_age, min_exposure_seconds=min_exp)
            self.last_memory_cleanup = now
        
        # Mode Change Detection & Logging
        current_mode = self.context.get("system_mode")
        if not hasattr(self, "_last_mode_logged") or self._last_mode_logged != current_mode:
            logger.info(f"System Mode: {current_mode}")
            self._last_mode_logged = current_mode
            
        # Periodic Status Heartbeat (every 5 seconds) - DEBUG level to keep console clean
        if int(now) % 5 == 0:
            if not hasattr(self, "_last_heartbeat_tick") or self._last_heartbeat_tick != int(now):
                logger.debug(f"[HEARTBEAT] Mode: {current_mode} | Object: {'Yes' if self.context['last_object_detection'] else 'No'}")
                self._last_heartbeat_tick = int(now)
        
        # Update shared IMU data for vision stabilization (Roll, Pitch, Yaw)
        if self.sensors and "imu" in self.sensors:
            imu_data = self.sensors["imu"].get_data()
            if imu_data:
                self.shared_imu[0] = getattr(imu_data, "roll", 0.0)
                self.shared_imu[1] = getattr(imu_data, "pitch", 0.0)
                self.shared_imu[2] = getattr(imu_data, "yaw", 0.0)
                
                # Apply Mechanical Stabilization (100Hz sync) - Skip in calibration
                if self.servo_ctrl and self.mech_stab_enabled and current_mode != "calibrate":
                    # Apply inversion
                    pitch_error = imu_data.pitch
                    if self.config.get("servos.camera.tilt.inverted", False):
                        pitch_error = -pitch_error
                    
                    # target_angle = base_tilt - body_pitch
                    target_tilt = self.context.get("target_tilt", 90)
                    stab_angle = target_tilt - pitch_error
                    # Clamp to safe limits
                    l_neg = self.config.get("servos.camera.tilt.limit_neg", 45)
                    l_pos = self.config.get("servos.camera.tilt.limit_pos", 45)
                    middle = self.config.get("servos.camera.tilt.middle", 90)
                    
                    delta_stab = stab_angle - middle
                    clamped_delta = max(-l_neg, min(l_pos, delta_stab))
                    stab_angle = middle + clamped_delta
                    
                    self.servo_ctrl.set_angle(self.tilt_channel, stab_angle)
        
        # Execute Behavior Tree - Skip in calibration mode to allow manual servo tests
        if current_mode != "calibrate":
            self.root.run()
        else:
            # In calibration mode, we just ensure no active gaits are overriding manually
            pass

    def stop(self):
        logger.info("Stopping Intelligence controller (Vision Process)...")
        self.vision.stop()
        # Wait for graceful stop with timeout, then force if needed
        self.vision.join(timeout=5.0)
        if self.vision.is_alive():
            logger.warning("Vision process did not stop gracefully, terminating.")
            self.vision.terminate()
        logger.info("Intelligence controller stopped")
