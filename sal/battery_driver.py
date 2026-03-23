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

        self.voltage_min = config.get("battery.voltage_min", 7.0)
        self.voltage_max = config.get("battery.voltage_max", 8.4)
        self.voltage_low = config.get("battery.voltage_low", 7.2)

        try:
            self.bus = smbus.SMBus(self.bus_id)
            self.cmd = 0x84
            self.data = BatteryStatus(
                timestamp=time.time(),
                metadata={},
                voltage=8.0,
                percentage=100,
                is_low=False,
            )
            logger.info("BatteryDriver (ADS7830) initialized")
            logger.info(
                f"Battery thresholds: low={self.voltage_low}V, min={self.voltage_min}V, max={self.voltage_max}V"
            )
        except Exception as e:
            logger.error(f"Failed to init BatteryDriver: {e}")
            raise

    def update(self) -> None:
        try:
            self.bus.write_byte(self.address, self.cmd)
            val = self.bus.read_byte(self.address)
            voltage = val / 255.0 * 5.0 * 2.0

            self.data.voltage = round(voltage, 2)
            voltage_range = self.voltage_max - self.voltage_min
            percentage = int((voltage - self.voltage_min) / voltage_range * 100)
            self.data.percentage = max(0, min(100, percentage))
            self.data.is_low = voltage < self.voltage_low
            self.data.timestamp = time.time()
        except Exception as e:
            logger.error(f"Battery update failed: {e}")

    def get_data(self) -> Optional[BatteryStatus]:
        return self.data

    def is_critical(self) -> bool:
        """Check if battery voltage is at critical level."""
        voltage_critical = self.config.get("battery.voltage_critical", 6.8)
        return self.data.voltage < voltage_critical
