import logging
from typing import Optional
from .base import IServoController
from utils.config import ConfigManager

try:
    import board
    import busio
    from adafruit_pca9685 import PCA9685
except ImportError:
    # This will be handled by the factory
    board = None

logger = logging.getLogger(__name__)

# The channel mapping and calibration are now loaded from config.yaml

class PCA9685Driver(IServoController):
    def __init__(self, config: ConfigManager):
        self.config = config
        self.address = config.get("hardware.pca9685_address", 0x40)
        self.bus_id = config.get("hardware.i2c_bus", 1)
        
        if board is None:
            raise ImportError("Adafruit libraries not found. Use simulation mode.")

        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.pca = PCA9685(self.i2c, address=self.address)
            self.pca.frequency = 50 # Standard for servos
            logger.info(f"PCA9685 initialized at address {hex(self.address)}")
        except Exception as e:
            logger.error(f"Failed to initialize PCA9685: {e}")
            raise

    def set_angle(self, channel: int, angle: float) -> None:
        duty = int(3276 + (angle / 180.0) * (6553 - 3276))
        self.pca.channels[channel].duty_cycle = duty

    def update_poses(self, poses: Dict[str, Any], ik_engine: Any) -> None:
        """Iterate through legs, calculate IK, and set servo angles with config offsets"""
        for leg_prefix, coords in poses.items():
            # config key is e.g. servos.leg_fl
            config_key = f"servos.leg_{leg_prefix}"
            leg_cfg = self.config.get(config_key)
            
            if leg_cfg:
                x, y, z = coords
                try:
                    angles = ik_engine.calculate_angles(x, y, z)
                    
                    # Mapping: Coxa/Femur/Tibia
                    for part in ["coxa", "femur", "tibia"]:
                        p_cfg = leg_cfg.get(part)
                        if p_cfg:
                            angle = getattr(angles, part)
                            # Apply inversion if specified
                            if p_cfg.get("inverted", False):
                                angle = -angle
                            
                            # Final angle = middle + calculated_ik
                            final_angle = p_cfg.get("middle", 90) + angle
                            
                            # Clamp to limits
                            final_angle = max(p_cfg.get("min", 20), min(p_cfg.get("max", 160), final_angle))
                            
                            self.set_angle(p_cfg.get("channel"), final_angle)
                            
                except Exception as e:
                    logger.debug(f"IK Error for leg {leg_prefix}: {e}")

    def release_all(self) -> None:
        for i in range(16):
            self.pca.channels[i].duty_cycle = 0
        logger.info("All servos released (PWM disabled)")
