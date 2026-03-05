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

        self.current_angles = {} # Store for live visualization
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
                    # Pass the servo limits to the IK engine so it calculates a physically achievable pose
                    angles = ik_engine.calculate_angles(x, y, z, limits=leg_cfg)
                    
                    # Mapping: Joint_1/2/3
                    for part in ["joint_1", "joint_2", "joint_3"]:
                        p_cfg = leg_cfg.get(part)
                        if p_cfg:
                            angle_ik = getattr(angles, part)
                            
                            # All joints now use 90 as the neutral midpoint in our IK
                            neutral = 90
                            delta = angle_ik - neutral
                            
                            # Apply inversion if specified
                            if p_cfg.get("inverted", False):
                                delta = -delta
                            
                            # Final angle = middle + delta (Limit is already applied in IK engine)
                            final_angle = p_cfg.get("middle", 90) + delta
                            
                            self.set_angle(p_cfg.get("channel"), final_angle)
                            
                            # Store for visualization (global servo state)
                            self.current_angles[f"{leg_prefix}_{part}"] = {
                                "angle": final_angle,
                                "raw_angle": angle_ik,
                                "channel": p_cfg.get("channel")
                            }
                            
                except Exception as e:
                    logger.debug(f"IK Error for leg {leg_prefix}: {e}")

    def release_all(self) -> None:
        for i in range(16):
            self.pca.channels[i].duty_cycle = 0
        self.current_angles.clear()
        logger.info("All servos released (PWM disabled)")

    def get_servos(self) -> Dict[str, Any]:
        return self.current_angles
