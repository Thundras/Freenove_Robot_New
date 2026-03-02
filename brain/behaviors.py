import logging
from .bt_core import Leaf

logger = logging.getLogger(__name__)

class FollowPerson(Leaf):
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context

    def run(self) -> bool:
        # Pillar 3 Enhancement: Only follow if mode is 'follow'
        if self.context.get("system_mode") != "follow":
            return False

        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "person":
            dist = detection.get("dist", 1000)
            center_x = detection.get("center_x", 0.5) # 0.0 to 1.0
            
            # --- CENTERING LOGIC ---
            # If person is to the left (center_x < 0.4), turn left. 
            # If to the right (center_x > 0.6), turn right.
            turn_rate = 0.0
            if center_x < 0.35:
                turn_rate = -0.5 # Turn Left
            elif center_x > 0.65:
                turn_rate = 0.5  # Turn Right
            
            if dist > 800:
                logger.info(f"Following person at {dist}mm (Turning: {turn_rate})")
                self.context["gait"].set_target_speed(0.5, turn_rate)
            else:
                # Still turn to face them even if standing still
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
        if "system_mode" not in self.context:
            self.context["system_mode"] = "autonomous"

    def run(self) -> bool:
        gesture = self.context.get("last_gesture")
        if not gesture:
            return False
            
        label = gesture["label"]
        if label == "COME":
            logger.info("Gesture: COME detected! Switching to FOLLOW mode.")
            self.context["system_mode"] = "follow"
            self.context["gait"].set_pose("normal")
            if "buzzer" in self.context["sensors"]:
                self.context["sensors"]["buzzer"].beep(0.1)
        elif label == "AWAY":
            logger.info("Gesture: AWAY detected! Switching to IDLE mode.")
            self.context["system_mode"] = "autonomous"
            self.context["gait"].set_target_speed(0.0)
            self.context["gait"].set_pose("normal")
            if "buzzer" in self.context["sensors"]:
                self.context["sensors"]["buzzer"].beep(0.05)
                time.sleep(0.05)
                self.context["sensors"]["buzzer"].beep(0.05)
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
            logger.warning(f"Obstacle detected at {distance}cm! Avoiding...")
            # Logic for avoidance: Stop or turn
            self.sensors.get("gait").set_target_speed(0.0, 0.5) # Turn on spot
            return True 
        
        return False # Failure (No avoidance needed)

class ExploreRoom(Leaf):
    def __init__(self, name, gait_sequencer, context=None):
        super().__init__(name)
        self.gait = gait_sequencer
        self.context = context

    def run(self) -> bool:
        """Just walk forward"""
        if self.context.get("system_mode") != "autonomous":
            return False
            
        logger.info("Exploring room...")
        self.gait.set_target_speed(0.5)
        return True
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
            return False
            
        detection = self.context.get("last_object_detection")
        if not detection or detection["label"] != "dog":
            # Reset pose if no dog detected
            self.context["gait"].set_pose("normal")
            return False

        interest = detection.get("interest", "unknown")
        dist = detection.get("dist", 2000)
        center_x = detection.get("center_x", 0.5)

        # Centering logic for dogs
        turn_rate = 0.0
        if center_x < 0.35:
            turn_rate = -0.4
        elif center_x > 0.65:
            turn_rate = 0.4

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
            return False

        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "ball":
            dist = detection.get("dist", 2000)
            center_x = detection.get("center_x", 0.5)

            # Centering logic
            turn_rate = 0.0
            if center_x < 0.35:
                turn_rate = -0.4
            elif center_x > 0.65:
                turn_rate = 0.4

            if dist < 400:
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
            
            # Happy beep when nudging
            if dist < 400 and "buzzer" in self.context["sensors"]:
                self.context["sensors"]["buzzer"].beep(0.05)

            return True
        
        # Reset LED if ball lost
        if "led" in self.context["sensors"]:
            self.context["sensors"]["led"].clear()
            
        return False

class SecurityMonitor(Leaf):
    def __init__(self, name, context):
        super().__init__(name)
        self.context = context

    def run(self) -> bool:
        if self.context.get("system_mode") != "alarm":
            return False

        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "person":
            logger.info("SECURITY ALERT: Person detected in ALARM mode!")
            self.context["gait"].set_target_speed(0.0)
            return True
        return False

class Idle(Leaf):
    def __init__(self, name, gait_sequencer):
        super().__init__(name)
        self.gait = gait_sequencer

    def run(self) -> bool:
        if self.gait.current_speed < 0.01:
            pass
        return True
