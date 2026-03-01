import smbus
import logging
import time
from typing import Optional
from .base import ISensor, BatteryStatus

logger = logging.getLogger(__name__)

class BatteryDriver(ISensor):
    def __init__(self, config):
        self.config = config
        self.bus_id = config.get("hardware.i2c_bus", 1)
        self.address = config.get("hardware.ads7830_address", 0x48)
        try:
            self.bus = smbus.SMBus(self.bus_id)
            self.cmd = 0x84
            self.data = BatteryStatus(
                timestamp=time.time(),
                metadata={},
                voltage=8.0,
                percentage=100,
                is_low=False
            )
            logger.info("BatteryDriver (ADS7830) initialized")
        except Exception as e:
            logger.error(f"Failed to init BatteryDriver: {e}")
            raise

    def update(self) -> None:
        try:
            # Modeled after Freenove ADS7830.py
            self.bus.write_byte(self.address, self.cmd)
            val = self.bus.read_byte(self.address)
            voltage = val / 255.0 * 5.0 * 2.0 # 2S Li-ion mapping
            
            self.data.voltage = round(voltage, 2)
            # 8.4V = 100%, 7.0V = 0%
            percentage = int((voltage - 7.0) / 1.4 * 100)
            self.data.percentage = max(0, min(100, percentage))
            self.data.is_low = voltage < 7.2
            self.data.timestamp = time.time()
        except Exception as e:
            logger.error(f"Battery update failed: {e}")

    def get_data(self) -> Optional[BatteryStatus]:
        return self.data
