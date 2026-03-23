import logging
import time
import math
from .bt_core import Leaf, ParameterLeaf

logger = logging.getLogger(__name__)


class FollowPerson(ParameterLeaf):
    def __init__(self, name, context, params):
        super().__init__(name, context, params)
        self.last_log_time = 0

    def run(self) -> bool:
        self._eval_params()
        # Relaxed check: Allow following/tracking in both dedicated 'follow' and 'autonomous' modes.
        if self.context.get("system_mode") not in ["follow", "autonomous"]:
            self.context["gait"].set_look_at(0.0, 0.0)
            # Mandatory state clearing
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].clear()
            return False

        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "person":
            # Parametrized values
            follow_dist = self.current_params.get("follow_dist", 800)
            max_speed = self.current_params.get("speed", 0.5)
            kp_pan = self.current_params.get("kp_pan", 2.0)
            kp_tilt = self.current_params.get("kp_tilt", 15.0)

            dist = detection.get("dist", 1000)
            center_x = detection.get("center_x", 0.5)

            error_x = center_x - 0.5
            turn_rate = error_x * kp_pan

            center_y = detection.get("center_y", 0.5)
            current_tilt = self.context.get("target_tilt", 90)
            error_y = center_y - 0.5
            if abs(error_y) > 0.05:
                self.context["target_tilt"] = current_tilt + (error_y * kp_tilt)

            if dist > follow_dist:
                if time.time() - self.last_log_time > 2.0:
                    logger.info(
                        f"Following person (Dist: {dist}mm, Turn: {turn_rate:.2f})"
                    )
                    self.last_log_time = time.time()
                self.context["gait"].set_target_speed(max_speed, turn_rate)
            else:
                self.context["gait"].set_target_speed(0.0, turn_rate)

            # --- EXPRESSIVE BODY GAZE ---
            body_yaw = error_x * 15.0
            body_pitch = (center_y - 0.5) * 10.0
            self.context["gait"].set_look_at(body_yaw, body_pitch)

            return True

        # Reset look-at if person lost
        self.context["gait"].set_look_at(0.0, 0.0)
        return False


class ReactToPerson(ParameterLeaf):
    def run(self) -> bool:
        self._eval_params()
        if self.context.get("system_mode") != "autonomous":
            return False

        react_dist = self.current_params.get("react_dist", 1200)
        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "person":
            dist = detection.get("dist", 1000)
            if dist < react_dist:
                logger.info(f"Reacting to person at {dist}mm! Stopping to say hi.")
                self.context["gait"].set_target_speed(0.0)
                if "buzzer" in self.context["sensors"]:
                    self.context["sensors"]["buzzer"].beep(0.1)
                return True
        return False


class HandleGesture(ParameterLeaf):
    """
    Advanced Vision: Toggles interaction modes based on gestures.
    WAVE/COME -> Start following.
    STOP/AWAY -> Go to idle.
    """

    def __init__(self, name, context, params=None):
        super().__init__(name, context, params)
        self.gesture_buffer = []  # Persistence filter
        self.last_handled_timestamp = 0  # Track unique vision updates
        if "system_mode" not in self.context:
            self.context["system_mode"] = "autonomous"

    def run(self) -> bool:
        self._eval_params()
        gesture = self.context.get("last_gesture")
        if not gesture:
            self.gesture_buffer = []
            return False

        label = gesture["label"]
        timestamp = gesture.get("timestamp", 0)
        current_mode = self.context.get("system_mode", "autonomous")

        # Persistence Filter: Only act if it's a NEW vision update and seen for X frames
        persistence = self.current_params.get("persistence", 3)

        if timestamp <= self.last_handled_timestamp:
            return False  # Already processed this specific vision update

        self.last_handled_timestamp = timestamp
        self.gesture_buffer.append(label)

        # Buffering Feedback: Subtle buzzer click on first frame of a gesture
        if len(self.gesture_buffer) == 1:
            if "buzzer" in self.context["sensors"]:
                self.context["sensors"]["buzzer"].beep(0.01)  # Ultra-short click

        if len(self.gesture_buffer) < persistence:
            return False

        if not all(g == label for g in self.gesture_buffer):
            logger.debug(f"Gesture buffer mismatch: {self.gesture_buffer}")
            self.gesture_buffer.pop(0)
            return False

        # Clear buffer after detection
        self.gesture_buffer = []

        # Pillar 3: Safety - Don't let gestures override high-priority modes like 'alarm'
        if current_mode == "alarm":
            logger.info(f"Gesture {label} ignored while in ALARM mode.")
            self.context["last_gesture"] = None
            return False

        # Pillar 8: Social Security - Use configurable trust threshold
        face_data = self.context.get("last_face")
        trust = face_data.get("trust", 0.0) if face_data else 0.0
        # Parametrized trust threshold
        threshold = self.current_params.get("trust_threshold", 0.45)

        if trust < threshold and label in ["COME", "SIT", "DOWN"]:
            # Log as warning to make it stand out
            logger.warning(
                f"SECURITY: Gesture {label} REFUSED! Trust: {trust:.2f} < Req: {threshold}"
            )
            if "buzzer" in self.context["sensors"]:
                # Indicate rejection with a specific sound
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
            if current_mode == "follow":
                logger.info(
                    "Gesture: AWAY detected! Stopping follow, resuming AUTONOMOUS."
                )
                self.context["system_mode"] = "autonomous"
                self.context["gait"].set_target_speed(0.0)
                self.context["gait"].set_pose("normal")
            else:
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


class AvoidObstacles(ParameterLeaf):
    def run(self) -> bool:
        self._eval_params()

        ultrasonic = self.context["sensors"].get("ultrasonic")
        if not ultrasonic:
            return False

        data = ultrasonic.get_data()
        distance = data.metadata.get("distance_cm", 100.0)

        avoid_dist = self.current_params.get("avoid_dist", 20.0)

        if distance < avoid_dist:
            # Check mode: Don't move if sitting or down
            current_mode = self.context.get("system_mode", "autonomous")
            if current_mode in ["sit", "down", "manual"]:
                logger.debug(
                    f"Obstacle at {distance}cm, but suppressed due to mode: {current_mode}"
                )
                return False

            logger.warning(f"Obstacle detected at {distance}cm! Avoiding...")
            gait = self.context.get("gait")
            if gait and hasattr(gait, "set_target_speed"):
                turn_speed = self.current_params.get("turn_speed", 0.5)
                gait.set_target_speed(0.0, turn_speed)  # Turn on spot
            return True

        return False


class SmartExplore(ParameterLeaf):
    """
    Battery-aware exploration:
    - Walks for max duration.
    - Sits/Lies down for designated time when near a wall/obstacle.
    """

    def __init__(self, name, context, params):
        super().__init__(name, context, params)
        self.state = "WALKING"
        self.state_start_time = time.time()
        self.last_turn_time = 0

    def run(self) -> bool:
        self._eval_params()
        if self.context.get("system_mode") != "autonomous":
            return False

        gait = self.context.get("gait")
        if not gait:
            return False

        now = time.time()
        elapsed = now - self.state_start_time

        # Parametrized values
        walk_speed = self.current_params.get("speed", 0.4)
        max_walk_time = self.current_params.get("max_walk_time", 120.0)
        rest_time = self.current_params.get("rest_time", 600.0)
        wall_dist = self.current_params.get("wall_dist", 40.0)

        # 1. State: WALKING
        if self.state == "WALKING":
            # Check for obstacles to trigger resting
            ultrasonic = self.context["sensors"].get("ultrasonic")
            distance = 100.0
            if ultrasonic:
                data = ultrasonic.get_data()
                if data:
                    distance = data.metadata.get("distance_cm", 100.0)

            # Rule: Only rest if near a wall and walked for at least 15s
            if distance < wall_dist and elapsed > 15.0:
                import random

                if random.random() < 0.4:  # 40% chance to settle down
                    self.state = random.choice(["SITTING", "LYING"])
                    self.state_start_time = now
                    logger.info(
                        f"SmartExplore: Found a cozy spot at {distance}cm. State -> {self.state}"
                    )
                    return True

            if elapsed > max_walk_time:
                # Force a turn to find a different wall
                if now - self.last_turn_time > 5.0:
                    logger.info(
                        "SmartExplore: Walking timeout. Searching for a wall..."
                    )
                    gait.set_target_speed(0.1, 0.6)
                    self.last_turn_time = now
                return True

            # Normal walking
            gait.set_target_speed(walk_speed)
            interest = self.context.get("play_interest", 1.0)
            self.context["play_interest"] = max(0.0, interest - 0.0005)
            return True

        # 2. States: SITTING / LYING
        elif self.state in ["SITTING", "LYING"]:
            interest = self.context.get("play_interest", 1.0)
            self.context["play_interest"] = min(1.0, interest + 0.002)

            if elapsed > rest_time:
                logger.info(
                    f"SmartExplore: Rest finished ({self.state}). State -> WALKING"
                )
                self.state = "WALKING"
                self.state_start_time = now
                gait.set_pose("normal")
                return True

            # Maintain posture
            gait.set_target_speed(0.0)
            pose = "sit" if self.state == "SITTING" else "down"
            gait.set_pose(pose)
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


class DogSocialInteraction(ParameterLeaf):
    """
    Social Behavior: Responds to other dogs with social cues.
    """

    def run(self) -> bool:
        self._eval_params()
        if self.context.get("system_mode") not in ["autonomous", "follow"]:
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].clear()
            return False

        detection = self.context.get("last_object_detection")
        if not detection or detection["label"] != "dog":
            self.context["gait"].set_pose("normal")
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].clear()
            self.context["gait"].set_look_at(0.0, 0.0)
            return False

        interest = detection.get("interest", "unknown")
        dist = detection.get("dist", 2000)
        center_x = detection.get("center_x", 0.5)

        # Parametrized gains
        kp_pan = self.current_params.get("kp_pan", 1.5)
        kp_tilt = self.current_params.get("kp_tilt", 10.0)

        # Centering logic for dogs
        error_x = center_x - 0.5
        turn_rate = error_x * kp_pan

        # Vertical head tracking
        center_y = detection.get("center_y", 0.5)
        error_y = center_y - 0.5
        if abs(error_y) > 0.05:
            current_tilt = self.context.get("target_tilt", 90)
            self.context["target_tilt"] = current_tilt + (error_y * kp_tilt)

        # --- EXPRESSIVE BODY GAZE ---
        body_yaw = error_x * 12.0
        body_pitch = error_y * 8.0
        self.context["gait"].set_look_at(body_yaw, body_pitch)

        if interest == "low":
            self.context["gait"].set_target_speed(0.0, turn_rate)
            self.context["gait"].set_pose("normal")
            return True

        if dist < self.current_params.get("submissive_dist", 600):
            self.context["gait"].set_pose("submissive")
            self.context["gait"].set_target_speed(0.0, turn_rate)
        elif dist < self.current_params.get("curious_dist", 1200):
            self.context["gait"].set_pose("normal")
            self.context["gait"].set_target_speed(0.0, turn_rate)

        return True


class PlayWithBall(ParameterLeaf):
    """Interacts with the red ball"""

    def run(self):
        self._eval_params()
        if self.context.get("system_mode") not in ["autonomous", "follow"]:
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].clear()
            return False

        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "ball":
            # Parametrized values
            min_interest = self.current_params.get("min_interest", 0.1)
            passive_interest = self.current_params.get("passive_interest", 0.4)
            close_dist = self.current_params.get("close_dist", 400)
            approach_dist = self.current_params.get("approach_dist", 1000)
            follow_speed = self.current_params.get("speed", 0.5)

            interest = self.context.get("play_interest", 1.0)
            dist = detection.get("dist", 2000)
            center_x = detection.get("center_x", 0.5)
            center_y = detection.get("center_y", 0.5)

            # --- MOOD LOGIC: Interest Thresholds ---
            if interest < min_interest:
                return False

            # Common: Always keep the gaze (Head Tracking)
            error_y = center_y - 0.5
            if abs(error_y) > 0.05:
                current_tilt = self.context.get("target_tilt", 90)
                self.context["target_tilt"] = current_tilt + (error_y * 12.0)

            # --- EXPRESSIVE BODY GAZE ---
            error_x = center_x - 0.5
            body_yaw = error_x * 15.0
            body_pitch = error_y * 10.0
            self.context["gait"].set_look_at(body_yaw, body_pitch)

            if interest < passive_interest:
                # Passive Interest: Just watch with the head, don't move
                if int(time.time() * 20) % 40 == 0:
                    logger.debug(
                        f"Play: Watching ball curiously (Low interest: {interest:.2f})"
                    )
                self.context["gait"].set_target_speed(0.0)
                return True

            # Full Interest: Active Play
            turn_rate = error_x * 1.8

            # Consume interest while actively playing
            self.context["play_interest"] = max(0.0, interest - 0.02)

            if dist < close_dist:
                if int(time.time() * 10) % 20 == 0:
                    logger.debug(f"Play: Ball is close ({dist}mm). Nudging!")
                self.context["gait"].set_pose("playful")
                self.context["gait"].set_target_speed(0.2, turn_rate)
            elif dist < approach_dist:
                logger.info(f"Play: Approaching ball ({dist}mm).")
                self.context["gait"].set_pose("normal")
                self.context["gait"].set_target_speed(0.4, turn_rate)
            else:
                self.context["gait"].set_target_speed(follow_speed, turn_rate)

            # Ball Detection Feedback (Green Spinning)
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].animate("spin", (0, 255, 0), speed=1.5)

            # Happy triple-beep
            if dist < close_dist and "buzzer" in self.context["sensors"]:
                if (
                    not hasattr(self, "_last_happy_beep")
                    or time.time() - self._last_happy_beep > 10.0
                ):
                    self.context["sensors"]["buzzer"].beep(0.05)
                    time.sleep(0.05)
                    self.context["sensors"]["buzzer"].beep(0.05)
                    time.sleep(0.05)
                    self.context["sensors"]["buzzer"].beep(0.1)
                    self._last_happy_beep = time.time()
                else:
                    self.context["sensors"]["buzzer"].beep(0.05)

            return True

        # Reset if ball lost
        if "led" in self.context["sensors"]:
            self.context["sensors"]["led"].clear()
        self.context["gait"].set_look_at(0.0, 0.0)
        if self.context.get("system_mode") in ["autonomous", "follow"]:
            self.context["gait"].set_pose("normal")
        return False


class ReactToFace(ParameterLeaf):
    """
    Social Behavior: Responds to people based on Trust Score
    """

    def run(self) -> bool:
        self._eval_params()
        if self.context.get("system_mode") not in ["autonomous", "follow"]:
            self.context["gait"].set_look_at(0.0, 0.0)
            return False

        detection = self.context.get("last_object_detection")
        face_data = self.context.get("last_face")

        if not detection or detection["label"] != "person":
            return False

        dist = detection.get("dist", 2000)
        center_x = detection.get("center_x", 0.5)
        trust = face_data.get("trust", 0.0) if face_data else 0.0

        # Parametrized thresholds
        stranger_thresh = self.current_params.get("stranger_threshold", 0.3)
        friend_thresh = self.current_params.get("friend_threshold", 0.8)

        # Centering logic (Proportional)
        error_x = center_x - 0.5
        turn_rate = error_x * self.current_params.get("kp_pan", 1.5)

        # --- EXPRESSIVE BODY GAZE ---
        center_y = detection.get("center_y", 0.5)
        error_y = center_y - 0.5
        body_yaw = error_x * 15.0
        body_pitch = error_y * 10.0
        self.context["gait"].set_look_at(body_yaw, body_pitch)

        # Case 1: STRANGER (Caution)
        if trust < stranger_thresh:
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].animate(
                    "pulse", (255, 100, 0)
                )  # Yellowish

            avoid_dist = self.current_params.get("stranger_avoid_dist", 1200)
            if dist < avoid_dist:
                self.context["gait"].set_target_speed(-0.3, turn_rate)
            else:
                self.context["gait"].set_target_speed(0.0, turn_rate)
            return True

        # Case 2: ACQUAINTANCE (Curiosity)
        elif trust < friend_thresh:
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].animate("pulse", (0, 255, 255))  # Cyan

            far_dist = self.current_params.get("acquaintance_far_dist", 1500)
            near_dist = self.current_params.get("acquaintance_near_dist", 1000)

            if dist > far_dist:
                self.context["gait"].set_target_speed(0.3, turn_rate)
            elif dist < near_dist:
                self.context["gait"].set_target_speed(-0.2, turn_rate)
            else:
                self.context["gait"].set_target_speed(0.0, turn_rate)
            return True

        # Case 3: FRIEND (Trust)
        else:
            if "led" in self.context["sensors"]:
                self.context["sensors"]["led"].animate("pulse", (0, 255, 0))  # Green

            follow_dist = self.current_params.get("friend_follow_dist", 800)
            personal_space = self.current_params.get("friend_personal_space", 400)

            if dist > follow_dist:
                self.context["gait"].set_target_speed(0.5, turn_rate)
            elif dist < personal_space:
                self.context["gait"].set_target_speed(-0.1, turn_rate)
            else:
                self.context["gait"].set_target_speed(0.0, turn_rate)
            return True

        self.context["gait"].set_look_at(0.0, 0.0)
        return False


class SecurityMonitor(ParameterLeaf):
    def run(self) -> bool:
        self._eval_params()
        if self.context.get("system_mode") != "alarm":
            self.context["gait"].set_look_at(0.0, 0.0)
            return False

        # Intruder alert: Always adopt aggressive posture in alarm mode
        self.context["gait"].set_pose("aggressive")

        detection = self.context.get("last_object_detection")
        if detection and detection["label"] == "person":
            dist = detection.get("dist", 2000)
            center_x = detection.get("center_x", 0.5)

            # Centering logic (Intruder Pursuit)
            kp_pan = self.current_params.get("kp_pan", 2.0)
            error_x = center_x - 0.5
            turn_rate = error_x * kp_pan

            # --- AGGRESSIVE BODY GAZE ---
            center_y = detection.get("center_y", 0.5)
            error_y = center_y - 0.5
            body_yaw = error_x * 20.0  # Wide aggressive gaze
            body_pitch = error_y * 15.0
            self.context["gait"].set_look_at(body_yaw, body_pitch)

            pursuit_dist = self.current_params.get("pursuit_dist", 600)
            pursuit_speed = self.current_params.get("speed", 0.6)

            if dist > pursuit_dist:
                logger.warning(f"SECURITY ALERT: Pursuing intruder at {dist}mm!")
                self.context["gait"].set_target_speed(pursuit_speed, turn_rate)
            else:
                logger.warning("SECURITY ALERT: Intruder cornered!")
                self.context["gait"].set_target_speed(0.0, turn_rate)

            return True  # Trigger AlarmPulse (LEDS/Buzzer)

        # No intruder: Stand guard
        self.context["gait"].set_target_speed(0.0)
        return False


class Idle(ParameterLeaf):
    def run(self) -> bool:
        """Fallback: Stop movement if no other behavior is active"""
        self._eval_params()
        gait = self.context.get("gait")
        if gait and gait.current_speed > 0.01:
            logger.debug("Idle: Stopping persistent movement.")
            gait.set_target_speed(0.0, 0.0)
        return True


class AmbientLook(ParameterLeaf):
    """Adds 'curiosity' by moving the head around when idle"""

    def __init__(self, name, context, params):
        super().__init__(name, context, params)
        self.last_move = 0
        self.target = 90

    def run(self) -> bool:
        self._eval_params()
        # Only look around if in autonomous and not busy with objects
        if self.context.get("system_mode") != "autonomous":
            self.context["gait"].set_look_at(0.0, 0.0)
            return False
        if self.context.get("last_object_detection"):
            return False

        now = time.time()
        interval = self.current_params.get("interval", 4.0)
        if now - self.last_move > interval:
            import random

            low = self.current_params.get("min_tilt", 70)
            high = self.current_params.get("max_tilt", 110)
            self.target = random.randint(low, high)
            self.last_move = now
            logger.debug(f"AmbientLook: Curious tilt to {self.target}")

        # Smoothly move towards target
        current = self.context.get("target_tilt", 90)
        if abs(current - self.target) > 1:
            step = 1 if self.target > current else -1
            self.context["target_tilt"] = current + step

            # Add subtle body yaw "peek" synced with head
            peek_factor = self.current_params.get("peek_factor", 0.2)
            peek_yaw = (current - 90) * peek_factor
            self.context["gait"].set_look_at(peek_yaw, 0.0)

        return False


class ExpressMood(ParameterLeaf):
    """
    Adds subtle, expressive body language using 6-DOF posing.
    """

    def __init__(self, name, context, params):
        super().__init__(name, context, params)
        self.phase = 0.0

    def run(self) -> bool:
        self._eval_params()
        mood = self.context.get("mood")
        if not mood or not self.context.get("gait"):
            return False

        dt = 0.05
        self.phase += dt

        # 1. Energy (Focus/Gaze)
        energy = mood.get("energy")
        pitch_bias = (1.0 - energy) * self.current_params.get(
            "energy_pitch_coeff", -10.0
        )
        height_offset = (1.0 - energy) * self.current_params.get(
            "energy_height_coeff", -15.0
        )

        # 2. Excitement (Vibrancy/Wobble)
        excitement = mood.get("excitement")
        roll_wobble = 0.0
        excitement_thresh = self.current_params.get("excitement_threshold", 0.6)
        if excitement > excitement_thresh:
            wobble_freq = self.current_params.get("wobble_freq_base", 2.0) + (
                excitement * self.current_params.get("wobble_freq_scale", 2.0)
            )
            wobble_amp = (excitement - excitement_thresh) * self.current_params.get(
                "wobble_amp_scale", 5.0
            )
            roll_wobble = math.sin(self.phase * wobble_freq) * wobble_amp

        # 3. Comfort (Presence/Stability)
        comfort = mood.get("comfort")
        crouch = (1.0 - comfort) * self.current_params.get(
            "comfort_crouch_coeff", -20.0
        )

        # Apply to Gait Engine
        gait = self.context["gait"]

        total_height_adj = height_offset + crouch
        final_height = max(60, gait.base_height + total_height_adj)

        gait.update_body_pose("z", total_height_adj)
        gait.update_body_pose("roll", roll_wobble)
        gait.update_body_pose("pitch", pitch_bias)

        return True


class AutoLevel(ParameterLeaf):
    """
    Reactive Stabilization: Uses IMU data to keep the trunk level.
    """

    def run(self) -> bool:
        self._eval_params()
        # Default to enabled if config missing
        enabled = self.current_params.get("enabled", True)
        strength = self.current_params.get("strength", 0.6)

        if not enabled or self.context.get("system_mode") == "calibrate":
            self.context["gait"].set_stabilization(0.0, 0.0)
            return False

        imu = self.context["sensors"].get("imu")
        if not imu:
            return False

        data = imu.get_data()
        if data:
            comp_roll = -data.roll * strength
            comp_pitch = -data.pitch * strength
            self.context["gait"].set_stabilization(comp_roll, comp_pitch)

        return True


class SniffAnimation(ParameterLeaf):
    """Expressive Behavior: Robot lowers its head and 'sniffs' the ground"""

    def __init__(self, name, context, params):
        super().__init__(name, context, params)
        self.start_time = time.time()

    def run(self) -> bool:
        self._eval_params()
        gait = self.context.get("gait")
        if not gait:
            return False

        elapsed = time.time() - self.start_time

        max_pitch = self.current_params.get("max_pitch", -15)
        max_sink = self.current_params.get("max_sink", -10)
        wobble_yaw_amp = self.current_params.get("yaw_amp", 8)
        wobble_pitch_amp = self.current_params.get("pitch_amp", 3)

        # Sniff cycle: Lower pitch, then subtle left/right head movements
        if elapsed < 1.0:
            # Lowering head
            gait.update_body_pose("pitch", max_pitch * elapsed)
            gait.update_body_pose("z", max_sink * elapsed)
        elif elapsed < 4.0:
            # Sniffing (wobble)
            cycle = elapsed - 1.0
            wobble_yaw = math.sin(cycle * 10) * wobble_yaw_amp
            wobble_pitch = max_pitch + math.sin(cycle * 15) * wobble_pitch_amp
            gait.update_body_pose("yaw", wobble_yaw)
            gait.update_body_pose("pitch", wobble_pitch)
            gait.update_body_pose("z", max_sink)
        else:
            return False

        return True
