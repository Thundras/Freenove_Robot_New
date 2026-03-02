import logging
import time
from .bt_core import Leaf

logger = logging.getLogger(__name__)

class FollowPerson(Leaf):
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context

    def run(self) -> bool:
        # Pillar 3 Enhancement: Only follow if mode is 'follow'
        if self.context.get("system_mode") != "follow":
            # Mandatory state clearing
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].clear()
            return False

        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "person":
            dist = detection.get("dist", 1000)
            center_x = detection.get("center_x", 0.5) # 0.0 to 1.0
            
            # --- PROPORTIONAL CENTERING LOGIC ---
            # center_x is 0.0 to 1.0. Error is center_x - 0.5.
            error_x = center_x - 0.5
            # Kp_pan: P-gain for horizontal turning. 1.0 means it turns at full speed if object is at the edge.
            turn_rate = error_x * 2.0 
            
            # --- ACTIVE VERTICAL GAZE (Tilt) ---
            # center_y is 0.0 to 1.0. If object is high (center_y < 0.3), tilt up. 
            center_y = detection.get("center_y", 0.5)
            # Use self.context.get("target_tilt", 90) as base.
            current_tilt = self.context.get("target_tilt", 90)
            # Adjust tilt proportionally to center_y error
            error_y = center_y - 0.5
            # Kp_tilt: P-gain for camera tilt.
            if abs(error_y) > 0.05:
                self.context["target_tilt"] = current_tilt + (error_y * 15.0) # Move 15 degrees max per frame correction
            
            if dist > 800:
                logger.info(f"Following person (Dist: {dist}mm, Turn: {turn_rate:.2f})")
                self.context["gait"].set_target_speed(0.5, turn_rate)
            else:
                self.context["gait"].set_target_speed(0.0, turn_rate)
            
            # Person Detection Feedback (Blue Breathing)
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].animate("breathe", (0, 0, 255), speed=1.0)
                
            return True
        return False

class ReactToPerson(Leaf):
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context

    def run(self) -> bool:
        """Simple reaction when a person is seen in autonomous mode"""
        if self.context.get("system_mode") != "autonomous":
            return False

        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "person":
            dist = detection.get("dist", 1000)
            if dist < 1200:
                logger.info(f"Reacting to person at {dist}mm! Stopping to say hi.")
                self.context["gait"].set_target_speed(0.0)
                if "buzzer" in self.context["sensors"]:
                    self.context["sensors"]["buzzer"].beep(0.1)
                return True
        return False

class HandleGesture(Leaf):
    """
    Advanced Vision: Toggles interaction modes based on gestures.
    WAVE/COME -> Start following.
    STOP/AWAY -> Go to idle.
    """
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context
        self.gesture_buffer = [] # Persistence filter
        self.last_handled_timestamp = 0 # Track unique vision updates
        if "system_mode" not in self.context:
            self.context["system_mode"] = "autonomous"

    def run(self) -> bool:
        gesture = self.context.get("last_gesture")
        if not gesture:
            self.gesture_buffer = []
            return False
            
        label = gesture["label"]
        timestamp = gesture.get("timestamp", 0)
        current_mode = self.context.get("system_mode", "autonomous")

        # Persistence Filter: Only act if it's a NEW vision update and seen for 3 frames
        if timestamp <= self.last_handled_timestamp:
            return False # Already processed this specific vision update
            
        self.last_handled_timestamp = timestamp
        self.gesture_buffer.append(label)
        
        if len(self.gesture_buffer) < 3:
            return False
            
        if not all(g == label for g in self.gesture_buffer):
            self.gesture_buffer.pop(0)
            return False
        
        # Clear buffer after detection
        self.gesture_buffer = []

        # Pillar 3: Safety - Don't let gestures override high-priority modes like 'alarm'
        if current_mode == "alarm":
            logger.info(f"Gesture {label} ignored while in ALARM mode.")
            self.context["last_gesture"] = None
            return False

        # Pillar 8: Social Security - Only obey trusted persons (>0.3 trust approx. 40 min)
        face_data = self.context.get("last_face")
        trust = face_data.get("trust", 0.0) if face_data else 0.0
        if trust < 0.3 and label in ["COME", "SIT", "DOWN"]:
            logger.info(f"Gesture {label} denied: Stranger or low trust (Trust: {trust:.2f})")
            if "buzzer" in self.context["sensors"]:
                # Lower pitch or longer beep for "Denied"
                self.context["sensors"]["buzzer"].beep(0.4) 
            self.context["last_gesture"] = None
            return False

        if label == "COME":
            logger.info("Gesture: COME detected! Switching to FOLLOW mode.")
            self.context["system_mode"] = "follow"
            self.context["gait"].set_pose("normal")
            if "buzzer" in self.context["sensors"]:
                self.context["sensors"]["buzzer"].beep(0.1)
        elif label == "AWAY":
            # Only reset if we are currently in follow mode.
            # Do NOT reset 'sit' or 'down' automatically, as no-hand detection (AWAY) 
            # would immediately override the user's manual pose command.
            if current_mode == "follow":
                logger.info("Gesture: AWAY detected! Stopping follow, resuming AUTONOMOUS.")
                self.context["system_mode"] = "autonomous"
                self.context["gait"].set_target_speed(0.0)
                self.context["gait"].set_pose("normal")
            else:
                # Silently ignore AWAY if we are in sit/down/manual
                return False
        elif label == "SIT":
            logger.info("Gesture: SIT detected! Entering STANDBY mode.")
            self.context["system_mode"] = "sit"
            self.context["gait"].set_target_speed(0.0)
            self.context["gait"].set_pose("sit")
            if "buzzer" in self.context["sensors"]:
                self.context["sensors"]["buzzer"].beep(0.2)
        elif label == "DOWN":
            logger.info("Gesture: DOWN detected! Entering SLEEP mode (Platz).")
            self.context["system_mode"] = "down"
            self.context["gait"].set_target_speed(0.0)
            self.context["gait"].set_pose("down")
            if "buzzer" in self.context["sensors"]:
                self.context["sensors"]["buzzer"].beep(0.3)
        
        # Clear gesture to avoid double triggering
        self.context["last_gesture"] = None
        return True

class AvoidObstacles(Leaf):
    def __init__(self, name, sensor_manager):
        super().__init__(name)
        self.sensors = sensor_manager

    def run(self) -> bool:
        ultrasonic = self.sensors.get("ultrasonic")
        if not ultrasonic:
            return False
            
        data = ultrasonic.get_data()
        distance = data.metadata.get("distance_cm", 100.0)
        
        if distance < 20.0:
            # Check mode: Don't move if sitting or down
            current_mode = self.sensors.get("intelligence").context.get("system_mode", "autonomous")
            if current_mode in ["sit", "down", "manual"]:
                logger.debug(f"Obstacle at {distance}cm, but suppressed due to mode: {current_mode}")
                return False

            logger.warning(f"Obstacle detected at {distance}cm! Avoiding...")
            # Logic for avoidance: Stop or turn
            self.sensors.get("gait").set_target_speed(0.0, 0.5) # Turn on spot
            return True 
        
        return False # Failure (No avoidance needed)

class SmartExplore(Leaf):
    """
    Battery-aware exploration: 
    - Walks for max 2 minutes.
    - Sits/Lies down for ~10 minutes when near a wall/obstacle.
    """
    def __init__(self, name, gait, context):
        super().__init__(name)
        self.gait = gait
        self.context = context
        self.state = "WALKING"
        self.state_start_time = time.time()
        self.last_turn_time = 0

    def run(self) -> bool:
        if self.context.get("system_mode") != "autonomous":
            return False

        now = time.time()
        elapsed = now - self.state_start_time
        
        # 1. State: WALKING (Max 2 mins)
        if self.state == "WALKING":
            # Check for obstacles to trigger resting
            ultrasonic = self.context["sensors"].get("ultrasonic")
            distance = 100.0
            if ultrasonic:
                data = ultrasonic.get_data()
                if data:
                    distance = data.metadata.get("distance_cm", 100.0)

            # Rule: Only rest if near a wall (< 40cm) and walked for at least 15s
            if distance < 40.0 and elapsed > 15.0:
                import random
                if random.random() < 0.4: # 40% chance to settle down
                    self.state = random.choice(["SITTING", "LYING"])
                    self.state_start_time = now
                    logger.info(f"SmartExplore: Found a cozy spot at {distance}cm. State -> {self.state}")
                    return True
            
            # Max walk time reached? Just stop and rest even if no wall? 
            # User said "nur neben hindernissen". So if no wall, just keep walking/turning.
            if elapsed > 120.0:
                # Force a turn to find a different wall
                if now - self.last_turn_time > 5.0:
                    logger.info("SmartExplore: Walking timeout. Searching for a wall...")
                    self.gait.set_target_speed(0.1, 0.6)
                    self.last_turn_time = now
                return True

            # Normal walking
            self.gait.set_target_speed(0.4)
            # Walking slightly drains interest (fatigue)
            interest = self.context.get("play_interest", 1.0)
            self.context["play_interest"] = max(0.0, interest - 0.0005)
            return True

        # 2. States: SITTING / LYING (~10 mins)
        elif self.state in ["SITTING", "LYING"]:
            # Resting restores interest
            interest = self.context.get("play_interest", 1.0)
            self.context["play_interest"] = min(1.0, interest + 0.002)
            
            if elapsed > 600.0: # 10 minutes
                logger.info("SmartExplore: Rest finished. Time to stretch! State -> WALKING")
                self.state = "WALKING"
                self.state_start_time = now
                self.gait.set_pose("normal")
                return True

            # Maintain posture
            self.gait.set_target_speed(0.0)
            pose = "sit" if self.state == "SITTING" else "down"
            self.gait.set_pose(pose)
            
            # Subtle feedback: occasional look around via AmbientLook is already running
            return True

        return False
class AlarmPulse(Leaf):
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context

    def run(self) -> bool:
        logger.warning("ALARM! Pulsing red LEDs.")
        if "led" in self.context["sensors"]:
            # Rapid red scanner effect
            self.context["sensors"]["led"].animate("scanner", (255, 0, 0), speed=2.0)
        if "buzzer" in self.context["sensors"]:
            self.context["sensors"]["buzzer"].on()
        return True

class DogSocialInteraction(Leaf):
    """
    Social Behavior: Responds to other dogs with social cues.
    - If dog is uninterested (moving away): Stop/Stay passive.
    - If dog is close: Crouch (submissive posture).
    - If dog is medium distance: Watch curiously.
    """
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context

    def run(self) -> bool:
        if self.context.get("system_mode") not in ["autonomous", "follow"]:
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].clear()
            return False
            
        detection = self.context.get("last_object_detection")
        if not detection or detection["label"] != "dog":
            # Reset pose if no dog detected
            self.context["gait"].set_pose("normal")
            if "led" in self.context["sensors"]:
                # Only clear if we were the one who set it (heuristic)
                # For now, just clear to be safe
                self.context["sensors"]["led"].clear()
            return False

        interest = detection.get("interest", "unknown")
        dist = detection.get("dist", 2000)
        center_x = detection.get("center_x", 0.5)

        # Centering logic for dogs (Proportional)
        error_x = center_x - 0.5
        turn_rate = error_x * 1.5
        
        # Vertical head tracking
        center_y = detection.get("center_y", 0.5)
        error_y = center_y - 0.5
        if abs(error_y) > 0.05:
            current_tilt = self.context.get("target_tilt", 90)
            self.context["target_tilt"] = current_tilt + (error_y * 10.0)

        if interest == "low":
            logger.info("Social: Other dog seems uninterested. Staying passive.")
            self.context["gait"].set_target_speed(0.0, turn_rate)
            self.context["gait"].set_pose("normal")
            return True

        if dist < 600:
            logger.info(f"Social: Dog is very close ({dist}mm). Adopting submissive pose.")
            self.context["gait"].set_pose("submissive")
            self.context["gait"].set_target_speed(0.0, turn_rate)
        elif dist < 1200:
            logger.info(f"Social: Dog detected at {dist}mm. Watching curiously.")
            self.context["gait"].set_pose("normal")
            self.context["gait"].set_target_speed(0.0, turn_rate)
        
        return True

class PlayWithBall(Leaf):
    """Interacts with the red ball"""
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context

    def run(self):
        if self.context.get("system_mode") not in ["autonomous", "follow"]:
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].clear()
            return False

        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "ball":
            interest = self.context.get("play_interest", 1.0)
            dist = detection.get("dist", 2000)
            center_x = detection.get("center_x", 0.5)
            center_y = detection.get("center_y", 0.5)

            # --- MOOD LOGIC: Interest Thresholds ---
            if interest < 0.1:
                # Disinterested: Ignore ball completely
                return False
            
            # Common: Always keep the gaze (Head Tracking) if interest > 0.1
            error_y = center_y - 0.5
            if abs(error_y) > 0.05:
                current_tilt = self.context.get("target_tilt", 90)
                self.context["target_tilt"] = current_tilt + (error_y * 12.0)

            if interest < 0.4:
                # Passive Interest: Just watch with the head, don't move
                error_x = center_x - 0.5
                # We could also use this to tilt a bit left/right if we had a pan servo, 
                # but for now we just STAY PUT.
                if int(time.time() * 20) % 40 == 0:
                    logger.info(f"Play: Watching ball curiously (Low interest: {interest:.2f})")
                self.context["gait"].set_target_speed(0.0)
                return True

            # Full Interest: Active Play
            # Centering logic (Proportional)
            error_x = center_x - 0.5
            turn_rate = error_x * 1.8
            
            # Consume interest while actively playing
            self.context["play_interest"] = max(0.0, interest - 0.02)

            if dist < 400:
                if int(time.time() * 10) % 20 == 0:
                    logger.info(f"Play: Ball is close ({dist}mm). Nudging!")
                self.context["gait"].set_pose("playful")
                self.context["gait"].set_target_speed(0.2, turn_rate)
            elif dist < 1000:
                logger.info(f"Play: Approaching ball ({dist}mm).")
                self.context["gait"].set_pose("normal")
                self.context["gait"].set_target_speed(0.4, turn_rate)
            else:
                self.context["gait"].set_target_speed(0.5, turn_rate)
            
            # Ball Detection Feedback (Green Spinning)
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].animate("spin", (0, 255, 0), speed=1.5)
            
            # Happy triple-beep when discovery (Emotional response)
            if dist < 400 and "buzzer" in self.context["sensors"]:
                if not hasattr(self, "_last_happy_beep") or time.time() - self._last_happy_beep > 10.0:
                    self.context["sensors"]["buzzer"].beep(0.05)
                    time.sleep(0.05)
                    self.context["sensors"]["buzzer"].beep(0.05)
                    time.sleep(0.05)
                    self.context["sensors"]["buzzer"].beep(0.1)
                    self._last_happy_beep = time.time()
                else:
                    self.context["sensors"]["buzzer"].beep(0.05)

            return True
        
        # Reset LED if ball lost
        if "led" in self.context["sensors"]:
            self.context["sensors"]["led"].clear()
            
        # Reset pose if ball lost and in autonomous/follow
        if self.context.get("system_mode") in ["autonomous", "follow"]:
            self.context["gait"].set_pose("normal")

        return False

class ReactToFace(Leaf):
    """
    Social Behavior: Responds to people based on Trust Score
    - Trusted (> 0.8): Follow closely.
    - Acquaintance (0.3 - 0.8): Watch curiously.
    - Stranger (< 0.3): Stay cautious, back away.
    """
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context

    def run(self) -> bool:
        if self.context.get("system_mode") not in ["autonomous", "follow"]:
            return False
            
        detection = self.context.get("last_object_detection")
        face_data = self.context.get("last_face")
        
        if not detection or detection["label"] != "person":
            return False
            
        dist = detection.get("dist", 2000)
        center_x = detection.get("center_x", 0.5)
        trust = face_data.get("trust", 0.0) if face_data else 0.0
        
        # Centering logic (Proportional)
        error_x = center_x - 0.5
        turn_rate = error_x * 1.5
        
        # Case 1: STRANGER (Caution)
        if trust < 0.3:
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].animate("pulse", (255, 100, 0)) # Yellowish
            
            if dist < 1200: # Stranger is too close!
                logger.info("ReactToFace: Stranger detected. Backing away for safety.")
                self.context["gait"].set_target_speed(-0.3, turn_rate)
            else:
                self.context["gait"].set_target_speed(0.0, turn_rate)
            return True

        # Case 2: ACQUAINTANCE (Curiosity)
        elif trust < 0.8:
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].animate("pulse", (0, 255, 255)) # Cyan
            
            # Keep a respectful distance
            if dist > 1500:
                self.context["gait"].set_target_speed(0.3, turn_rate)
            elif dist < 1000:
                self.context["gait"].set_target_speed(-0.2, turn_rate)
            else:
                self.context["gait"].set_target_speed(0.0, turn_rate)
            return True

        # Case 3: FRIEND (Trust)
        else:
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].animate("pulse", (0, 255, 0)) # Green
            
            # Follow closely
            if dist > 800:
                self.context["gait"].set_target_speed(0.5, turn_rate)
            elif dist < 400:
                self.context["gait"].set_target_speed(-0.1, turn_rate)
            else:
                self.context["gait"].set_target_speed(0.0, turn_rate)
            return True

        return False

class SecurityMonitor(Leaf):
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context

    def run(self) -> bool:
        if self.context.get("system_mode") != "alarm":
            return False

        # Intruder alert: Always adopt aggressive posture in alarm mode
        self.context["gait"].set_pose("aggressive")

        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "person":
            dist = detection.get("dist", 2000)
            center_x = detection.get("center_x", 0.5)

            # Centering logic (Intruder Pursuit)
            turn_rate = 0.0
            if center_x < 0.35:
                turn_rate = -0.5
            elif center_x > 0.65:
                turn_rate = 0.5

            if dist > 600:
                logger.warning(f"SECURITY ALERT: Pursuing intruder at {dist}mm!")
                self.context["gait"].set_target_speed(0.6, turn_rate)
            else:
                logger.warning("SECURITY ALERT: Intruder cornered!")
                self.context["gait"].set_target_speed(0.0, turn_rate)
            
            return True # Trigger AlarmPulse (LEDS/Buzzer)
        
        # No intruder: Stand guard
        self.context["gait"].set_target_speed(0.0)
        return False

class Idle(Leaf):
    def __init__(self, name, gait_sequencer):
        super().__init__(name)
        self.gait = gait_sequencer

    def run(self) -> bool:
        """Fallback: Stop movement if no other behavior is active"""
        if self.gait.current_speed > 0.01:
            logger.info("Idle: Stopping persistent movement.")
            self.gait.set_target_speed(0.0, 0.0)
        return True

class AmbientLook(Leaf):
    """Adds 'curiosity' by moving the head around when idle"""
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context
        self.last_move = 0
        self.target = 90

    def run(self) -> bool:
        # Only look around if in autonomous and not busy with objects
        if self.context.get("system_mode") != "autonomous":
            return False
        if self.context.get("last_object_detection"):
            return False
            
        now = time.time()
        if now - self.last_move > 4.0: # Every 4 seconds
            # Random tilt between 70 and 110
            import random
            self.target = random.randint(70, 110)
            self.last_move = now
            logger.debug(f"AmbientLook: Curious tilt to {self.target}")
        
        # Smoothly move towards target
        current = self.context.get("target_tilt", 90)
        if abs(current - self.target) > 1:
            step = 1 if self.target > current else -1
            self.context["target_tilt"] = current + step
            
        return False # Return false to allow other low-prio behaviors to run (like Idle)
