from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class SensorData:
    """Base class for all sensor data packets"""
    timestamp: float
    metadata: Dict[str, Any]

@dataclass
class IMUData(SensorData):
    roll: float
    pitch: float
    yaw: float
    accel_x: float
    accel_y: float
    accel_z: float

@dataclass
class BatteryStatus(SensorData):
    voltage: float
    percentage: int
    is_low: bool

class IServoController(ABC):
    """Interface for controlling the PCA9685 or similar PWM drivers"""
    @abstractmethod
    def update_poses(self, poses: Dict[str, Any], ik_engine: Any) -> None:
        """Convert (x,y,z) coordinates to servo angles and move servos"""
        pass

    @abstractmethod
    def release_all(self) -> None:
        """Relax all servos (stop PWM)"""
        pass

class ISensor(ABC):
    """Interface for all sensors (IMU, Ultrasonic, etc.)"""
    @abstractmethod
    def update(self) -> None:
        """Poll the hardware for new data"""
        pass

    @abstractmethod
    def get_data(self) -> Optional[SensorData]:
        """Return the latest cached data"""
        pass
