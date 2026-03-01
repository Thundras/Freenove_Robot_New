import logging
import time
from typing import Optional
from .base import ISensor, IMUData
from utils.config import ConfigManager

try:
    import board
    import adafruit_mpu6050
except ImportError:
    board = None

logger = logging.getLogger(__name__)

class IMUDriver(ISensor):
    def __init__(self, config: ConfigManager):
        self.config = config
        self.address = config.get("hardware.mpu6050_address", 0x68)
        
        if board is None:
            raise ImportError("Adafruit libraries not found.")

        try:
            self.i2c = board.I2C()
            self.sensor = adafruit_mpu6050.MPU6050(self.i2c, address=self.address)
            self._data: Optional[IMUData] = None
            logger.info(f"MPU6050 initialized at address {hex(self.address)}")
        except Exception as e:
            logger.error(f"Failed to initialize MPU6050: {e}")
            raise

    def update(self) -> None:
        accel_x, accel_y, accel_z = self.sensor.acceleration
        gyro_x, gyro_y, gyro_z = self.sensor.gyro
        
        # Simple Complementary Filter or direct pass-through for now
        # Roll and Pitch calculation from accelerometer
        roll = 180 * (math.atan2(accel_y, accel_z)) / math.pi
        pitch = 180 * (math.atan2(-accel_x, math.sqrt(accel_y**2 + accel_z**2))) / math.pi

        self._data = IMUData(
            timestamp=time.time(),
            metadata={},
            roll=roll,
            pitch=pitch,
            yaw=0.0, # Yaw requires magnetometer or integration
            accel_x=accel_x,
            accel_y=accel_y,
            accel_z=accel_z
        )

    def get_data(self) -> Optional[IMUData]:
        return self._data
