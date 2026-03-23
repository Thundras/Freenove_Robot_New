import time
import math
import logging
from typing import Optional, List, Dict, Any
from utils.config import ConfigManager
from .base import IServoController, ISensor, SensorData, IMUData, BatteryStatus

logger = logging.getLogger(__name__)


class MockServoController(IServoController):
    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config
        self.angles: Dict[str, Any] = {}
        logger.debug("MockServoController initialized")

    def set_angle(self, channel: int, angle: float) -> None:
        self.angles[str(channel)] = angle

    def update_poses(self, poses: Dict[str, Any], ik_engine: Any) -> None:
        """Mock: Calculate angles respecting config (inversion/middle/clamp)"""
        for leg_prefix, coords in poses.items():
            # config key is e.g. servos.leg_fl
            leg_cfg = None
            if self.config:
                leg_cfg = self.config.get(f"servos.leg_{leg_prefix}")

            x, y, z = coords
            try:
                # Pass the servo limits to the IK engine so it calculates a physically achievable pose
                angles = ik_engine.calculate_angles(x, y, z, limits=leg_cfg)

                # Mapping: config uses joint_1/2/3, LegAngles uses shoulder/thigh/shin
                config_to_field = {
                    "joint_1": "shoulder",
                    "joint_2": "thigh",
                    "joint_3": "shin",
                }
                for config_key in ["joint_1", "joint_2", "joint_3"]:
                    p_cfg = {}
                    if leg_cfg:
                        p_cfg = leg_cfg.get(config_key, {})

                    field_name = config_to_field[config_key]
                    angle_ik = getattr(angles, field_name)

                    # All joints now use 90 as the neutral midpoint in our IK
                    neutral = 90
                    delta = angle_ik - neutral

                    # Apply inversion
                    if p_cfg.get("inverted", False):
                        delta = -delta

                    # Final angle = middle + delta
                    middle = p_cfg.get("middle", 90)
                    final_angle = middle + delta

                    self.angles[f"{leg_prefix}_{field_name}"] = {
                        "angle": final_angle,
                        "raw_angle": angle_ik,
                        "channel": p_cfg.get("channel", -1),
                    }
            except Exception as e:
                logger.debug(f"Mock IK Error for leg {leg_prefix}: {e}")

    def release_all(self) -> None:
        logger.info("Mock: All servos released")
        self.angles.clear()

    def get_servos(self) -> Dict[str, Any]:
        return self.angles


class MockIMU(ISensor):
    def __init__(self):
        self.data = IMUData(
            timestamp=time.time(),
            metadata={},
            roll=0.0,
            pitch=0.0,
            yaw=0.0,
            accel_x=0.0,
            accel_y=0.0,
            accel_z=1.0,
        )
        self._target_roll = 0.0
        self._target_pitch = 0.0
        self._target_yaw = 0.0
        self._smoothing = 0.1
        self._jitter = 0.0
        self._oscillation_freq = 0.0
        self._oscillation_amp = 0.0
        self._oscillation_phase = 0.0
        self._start_time = time.time()

    def set_movement(self, roll: float, pitch: float, yaw: float) -> None:
        self._target_roll = roll
        self._target_pitch = pitch
        self._target_yaw = yaw

    def set_smoothing(self, factor: float) -> None:
        self._smoothing = max(0.01, min(1.0, factor))

    def set_jitter(self, level: float) -> None:
        self._jitter = max(0.0, min(10.0, level))

    def set_oscillation(self, freq: float, amplitude: float) -> None:
        self._oscillation_freq = max(0.0, freq)
        self._oscillation_amp = max(0.0, amplitude)

    def reset(self) -> None:
        self._target_roll = 0.0
        self._target_pitch = 0.0
        self._target_yaw = 0.0
        self.data.roll = 0.0
        self.data.pitch = 0.0
        self.data.yaw = 0.0
        self.data.accel_x = 0.0
        self.data.accel_y = 0.0
        self.data.accel_z = 1.0
        self._oscillation_freq = 0.0
        self._oscillation_amp = 0.0
        self._start_time = time.time()

    def update(self) -> None:
        self.data.timestamp = time.time()

        import random

        jitter_x = (
            random.uniform(-self._jitter, self._jitter) if self._jitter > 0 else 0.0
        )
        jitter_y = (
            random.uniform(-self._jitter, self._jitter) if self._jitter > 0 else 0.0
        )

        oscillation_offset = 0.0
        if self._oscillation_freq > 0 and self._oscillation_amp > 0:
            elapsed = time.time() - self._start_time
            oscillation_offset = self._oscillation_amp * math.sin(
                2 * math.pi * self._oscillation_freq * elapsed
            )

        self.data.roll = self._lerp(
            self.data.roll,
            self._target_roll + oscillation_offset + jitter_x,
            self._smoothing,
        )
        self.data.pitch = self._lerp(
            self.data.pitch,
            self._target_pitch + oscillation_offset + jitter_y,
            self._smoothing,
        )
        self.data.yaw = self._lerp(
            self.data.yaw, self._target_yaw + jitter_x, self._smoothing
        )

        self.data.accel_x = math.sin(math.radians(self.data.roll)) * 9.81
        self.data.accel_y = math.sin(math.radians(self.data.pitch)) * 9.81
        self.data.accel_z = (
            math.cos(math.radians(self.data.roll))
            * math.cos(math.radians(self.data.pitch))
            * 9.81
        )

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    def get_data(self) -> IMUData:
        return self.data


class MockBattery(ISensor):
    def __init__(self):
        self.data = BatteryStatus(
            timestamp=time.time(), metadata={}, voltage=8.0, percentage=95, is_low=False
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
        self.is_beeping = False
        self.stop_time = 0

    def beep(self, duration=0.1):
        logger.debug(f"Mock Buzzer: BEEP ({duration}s)")
        self.is_beeping = True
        self.stop_time = time.time() + duration

    def on(self):
        self.is_beeping = True
        self.stop_time = time.time() + 999999  # Forever

    def off(self):
        self.is_beeping = False
        self.stop_time = 0

    def update(self):
        if self.is_beeping and time.time() > self.stop_time:
            self.is_beeping = False


class MockLed:
    def __init__(self):
        self.num_pixels = 7
        self.pixels = [[0, 0, 0]] * self.num_pixels
        self.current_state = {
            "pattern": "off",
            "color": [0, 0, 0],
            "pixels": self.pixels,
        }

    def set_color(self, index, r, g, b):
        if 0 <= index < self.num_pixels:
            self.pixels[index] = [r, g, b]
        self.current_state = {
            "pattern": "manual",
            "color": [r, g, b],
            "pixels": self.pixels,
        }

    def fill(self, r, g, b):
        self.pixels = [[r, g, b]] * self.num_pixels
        self.current_state = {
            "pattern": "manual",
            "color": [r, g, b],
            "pixels": self.pixels,
        }

    def show(self):
        pass

    def animate(self, pattern, color, speed=1.0):
        # In a mock, we don't simulate the step-by-step animation of individual pixels
        # but we can fill the pixels list with the color to show it's active
        self.pixels = [list(color)] * self.num_pixels
        self.current_state = {
            "pattern": pattern,
            "color": list(color),
            "pixels": self.pixels,
        }

    def clear(self):
        self.pixels = [[0, 0, 0]] * self.num_pixels
        self.current_state = {
            "pattern": "off",
            "color": [0, 0, 0],
            "pixels": self.pixels,
        }

    def set_pattern(self, pattern: str, color: list):
        """Set a named animation pattern with color."""
        if pattern == "off":
            self.clear()
            return

        color_list = list(color) if not isinstance(color, list) else color
        self.pixels = [color_list] * self.num_pixels
        self.current_state = {
            "pattern": pattern,
            "color": color_list,
            "pixels": self.pixels,
        }


class MockGait:
    def __init__(self):
        self.target_speed = 0.0
        self.turn_rate = 0.0
        self.current_pose = "normal"
        self.current_speed = 0.0
        self.look_at_yaw = 0.0
        self.look_at_pitch = 0.0

    def set_target_speed(self, speed, turn=0.0):
        self.target_speed = speed
        self.turn_rate = turn

    def set_pose(self, pose_name):
        self.current_pose = pose_name

    def set_look_at(self, yaw, pitch):
        self.look_at_yaw = yaw
        self.look_at_pitch = pitch

    def update(self, dt):
        self.current_speed = self.target_speed
