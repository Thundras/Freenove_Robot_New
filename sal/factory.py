import logging
from .base import IServoController, ISensor
from .mock_drivers import MockServoController, MockIMU, MockBattery
from utils.config import ConfigManager

logger = logging.getLogger(__name__)

class SalFactory:
    @staticmethod
    def get_servo_controller(config: ConfigManager) -> IServoController:
        sim_mode = config.get("system.simulation_mode", True)
        if sim_mode:
            return MockServoController()
        
        try:
            from .pca9685_driver import PCA9685Driver
            return PCA9685Driver(config)
        except ImportError:
            logger.error("Could not import PCA9685Driver. Falling back to Mock.")
            return MockServoController()

    @staticmethod
    def get_imu(config: ConfigManager) -> ISensor:
        sim_mode = config.get("system.simulation_mode", True)
        if sim_mode:
            return MockIMU()
        
        try:
            from .imu_driver import IMUDriver
            return IMUDriver(config)
        except ImportError:
            logger.error("Could not import IMUDriver. Falling back to Mock.")
            return MockIMU()

    @staticmethod
    def get_battery(config: ConfigManager) -> ISensor:
        sim_mode = config.get("system.simulation_mode", True)
        if sim_mode:
            return MockBattery()
        
        try:
            from .battery_driver import BatteryDriver
            return BatteryDriver(config)
        except ImportError:
            logger.error("Could not import BatteryDriver. Falling back to Mock.")
            return MockBattery()
    @staticmethod
    def get_ultrasonic(config: ConfigManager) -> ISensor:
        sim_mode = config.get("system.simulation_mode", True)
        if sim_mode:
            from .mock_drivers import MockUltrasonic
            return MockUltrasonic()
        
        try:
            from .ultrasonic_driver import UltrasonicDriver
            return UltrasonicDriver(config)
        except ImportError:
            logger.error("Could not import UltrasonicDriver. Falling back to Mock.")
            from .mock_drivers import MockUltrasonic
            return MockUltrasonic()

    @staticmethod
    def get_buzzer(config: ConfigManager):
        sim_mode = config.get("system.simulation_mode", True)
        if sim_mode:
            from .mock_drivers import MockBuzzer
            return MockBuzzer()
        try:
            from .buzzer_driver import BuzzerDriver
            return BuzzerDriver(config)
        except Exception:
            from .mock_drivers import MockBuzzer
            return MockBuzzer()

    @staticmethod
    def get_led(config: ConfigManager):
        sim_mode = config.get("system.simulation_mode", True)
        if sim_mode:
            from .mock_drivers import MockLed
            return MockLed()
        try:
            from .led_driver import LedDriver
            return LedDriver(config)
        except Exception:
            from .mock_drivers import MockLed
            return MockLed()
