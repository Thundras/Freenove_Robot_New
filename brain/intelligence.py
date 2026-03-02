import logging
import multiprocessing
import time
from .bt_core import Selector, Sequence
from .behaviors import AvoidObstacles, ExploreRoom, ReactToPerson, FollowPerson, Idle, HandleGesture, AlarmPulse, SecurityMonitor, DogSocialInteraction, PlayWithBall
from .vision import VisionProcess

logger = logging.getLogger(__name__)

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
            "last_gesture": None,
            "system_mode": "autonomous" # autonomous, manual, sit, down
        }
        
        # Vision Process for AI (Offloaded)
        # Use maxsize to prevent memory bloat and blockages if consumer (WebServer) stops
        self.result_queue = multiprocessing.Queue(maxsize=10)
        self.frame_queue = multiprocessing.Queue(maxsize=2)
        self.shared_imu = multiprocessing.Array('d', [0.0, 0.0, 0.0]) # [Roll, Pitch, Yaw]
        
        self.vision = VisionProcess(
            self.result_queue, 
            self.frame_queue, 
            config, 
            shared_imu=self.shared_imu
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
        avoid = AvoidObstacles("AvoidObstacles", self.sensors)
        gesture = HandleGesture("HandleGesture", self.context)
        react = ReactToPerson("ReactToPerson", self.context)
        follow = FollowPerson("FollowPerson", self.context)
        social = DogSocialInteraction("DogSocialInteraction", self.context)
        ball = PlayWithBall("PlayWithBall", self.context)
        explore = ExploreRoom("ExploreRoom", self.gait, self.context)
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
        # 7. Defaults (Explore/Idle)
        root = Selector("MainBrain", [avoid, alarm_branch, gesture, ball, social, interaction, explore, idle])
        return root

    def start(self):
        self.vision.start()
        logger.info("Intelligence controller started")

    def update(self):
        """Standard update loop (called from main)"""
        while not self.result_queue.empty():
            data = self.result_queue.get()
            if data.get("type") == "object":
                self.context["last_object_detection"] = data
            elif data.get("type") == "gesture":
                self.context["last_gesture"] = data
            elif data.get("type") == "tilt_request":
                self.tilt_angle = data.get("angle", 90)
        
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
                    stab_angle = self.tilt_angle - pitch_error
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
