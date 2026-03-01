import time
import logging
from typing import Optional
from .base import ISensor, SensorData
try:
    from gpiozero import DistanceSensor
except ImportError:
    DistanceSensor = None

logger = logging.getLogger(__name__)

class UltrasonicDriver(ISensor):
    def __init__(self, config):
        self.config = config
        self.trigger = config.get("hardware.ultrasonic_trigger", 27)
        self.echo = config.get("hardware.ultrasonic_echo", 22)
        self.distance = 100.0
        
        if DistanceSensor is None:
            raise ImportError("gpiozero not found")
            
        try:
            self.sensor = DistanceSensor(echo=self.echo, trigger=self.trigger, max_distance=3)
            logger.info("UltrasonicDriver initialized")
        except Exception as e:
            logger.error(f"Failed to init Ultrasonic: {e}")
            raise

    def update(self) -> None:
        try:
            # Distance in meters, convert to cm
            self.distance = self.sensor.distance * 100.0
        except Exception as e:
            logger.error(f"Ultrasonic update failed: {e}")

    def get_data(self) -> Optional[SensorData]:
        return SensorData(
            timestamp=time.time(),
            metadata={"distance_cm": self.distance}
        )
