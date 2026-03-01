import time
import logging
from typing import Optional, List, Dict, Any
from .base import IServoController, ISensor, SensorData, IMUData, BatteryStatus

logger = logging.getLogger(__name__)

class MockServoController(IServoController):
    def __init__(self):
        self.angles: Dict[int, float] = {}
        logger.info("MockServoController initialized")

    def set_angle(self, channel: int, angle: float) -> None:
        self.angles[channel] = angle
        
    def update_poses(self, poses: Dict[str, Any], ik_engine: Any) -> None:
        """Mock: Just calculate angles but don't move anything"""
        for leg, coords in poses.items():
            x, y, z = coords
            try:
                ik_engine.calculate_angles(x, y, z)
            except:
                pass

    def release_all(self) -> None:
        logger.info("Mock: All servos released")
        self.angles.clear()

class MockIMU(ISensor):
    def __init__(self):
        self.data = IMUData(
            timestamp=time.time(),
            metadata={},
            roll=0.0, pitch=0.0, yaw=0.0,
            accel_x=0.0, accel_y=0.0, accel_z=1.0 # 1G
        )

    def update(self) -> None:
        # Simulate slight jitter/drift
        self.data.timestamp = time.time()
        # In a more advanced mock, we would use the last known servo angles
        # to calculate a simulated orientation
        pass

    def get_data(self) -> IMUData:
        return self.data

class MockBattery(ISensor):
    def __init__(self):
        self.data = BatteryStatus(
            timestamp=time.time(),
            metadata={},
            voltage=8.0,
            percentage=95,
            is_low=False
        )

    def update(self) -> None:
        self.data.timestamp = time.time()
        # Simulate battery drain over time if needed
        pass

    def get_data(self) -> BatteryStatus:
        return self.data

class MockUltrasonic(ISensor):
    def __init__(self):
        self.distance = 100.0
    def update(self):
        pass
    def get_data(self) -> SensorData:
        return SensorData(time.time(), {"distance_cm": self.distance})

class MockBuzzer:
    def __init__(self):
        pass
    def beep(self, duration=0.1):
        logger.info(f"Mock Buzzer: BEEP ({duration}s)")
    def on(self):
        pass
    def off(self):
        pass

class MockLed:
    def __init__(self):
        pass
    def set_color(self, index, r, g, b):
        pass
    def fill(self, r, g, b):
        pass
    def show(self):
        pass
    def animate(self, pattern, color, speed=1.0):
        pass
    def clear(self):
        pass

class MockGait:
    def __init__(self):
        self.target_speed = 0.0
        self.turn_rate = 0.0
        self.current_pose = "normal"
        self.current_speed = 0.0

    def set_target_speed(self, speed, turn=0.0):
        self.target_speed = speed
        self.turn_rate = turn

    def set_pose(self, pose_name):
        self.current_pose = pose_name

    def update(self, dt):
        self.current_speed = self.target_speed
