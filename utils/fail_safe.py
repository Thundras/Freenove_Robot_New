import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FailSafeState(Enum):
    NORMAL = "normal"
    IMU_TIMEOUT = "imu_timeout"
    ULTRASONIC_TIMEOUT = "ultrasonic_timeout"
    VISION_DEAD = "vision_dead"
    SERVO_ERROR = "servo_error"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class SensorHealth:
    name: str
    last_update: float
    timeout_threshold: float
    is_healthy: bool = True
    consecutive_failures: int = 0


@dataclass
class FailSafeConfig:
    imu_timeout: float = 2.0
    ultrasonic_timeout: float = 1.0
    max_consecutive_failures: int = 3
    speed_reduction_factor: float = 0.5


class FailSafeManager:
    def __init__(self, config: Optional[Any] = None):
        if config is None:
            self.config = FailSafeConfig()
        elif isinstance(config, FailSafeConfig):
            self.config = config
        else:
            self.config = FailSafeConfig(
                imu_timeout=config.get("system.fail_safe_imu_timeout", 2.0),
                ultrasonic_timeout=config.get(
                    "system.fail_safe_ultrasonic_timeout", 1.0
                ),
                max_consecutive_failures=config.get("system.fail_safe_max_failures", 3),
                speed_reduction_factor=config.get(
                    "system.fail_safe_speed_reduction", 0.5
                ),
            )

        self.sensors: Dict[str, SensorHealth] = {
            "imu": SensorHealth("imu", time.time(), self.config.imu_timeout),
            "ultrasonic": SensorHealth(
                "ultrasonic", time.time(), self.config.ultrasonic_timeout
            ),
        }

        self.current_state = FailSafeState.NORMAL
        self.active_failsafes: Dict[str, bool] = {
            "imu": False,
            "ultrasonic": False,
            "vision": False,
            "servo": False,
        }

        self.speed_multiplier = 1.0
        self.last_heartbeat: Dict[str, float] = {}

        logger.info("FailSafeManager initialized")

    def update_sensor_heartbeat(self, sensor_name: str) -> None:
        if sensor_name in self.sensors:
            self.sensors[sensor_name].last_update = time.time()
            self.sensors[sensor_name].is_healthy = True
            self.sensors[sensor_name].consecutive_failures = 0
        self.last_heartbeat[sensor_name] = time.time()

    def check_sensor_health(self, sensor_name: str) -> bool:
        if sensor_name not in self.sensors:
            return True

        sensor = self.sensors[sensor_name]
        now = time.time()
        time_since_update = now - sensor.last_update

        if time_since_update > sensor.timeout_threshold:
            sensor.consecutive_failures += 1
            sensor.is_healthy = False

            if sensor.consecutive_failures >= self.config.max_consecutive_failures:
                logger.warning(f"Sensor {sensor_name} failed health check")
                return False

        return True

    def set_state(self, state: FailSafeState) -> None:
        if state != self.current_state:
            old_state = self.current_state
            self.current_state = state
            logger.warning(f"Fail-safe state: {old_state.value} -> {state.value}")

    def trigger_failsafe(self, source: str, state: FailSafeState) -> None:
        self.active_failsafes[source] = True
        self.set_state(state)

        if source == "imu":
            self.speed_multiplier = 0.0
        elif source == "ultrasonic":
            self.speed_multiplier = self.config.speed_reduction_factor

        logger.critical(f"FAIL-SAFE TRIGGERED: {source} -> {state.value}")

    def clear_failsafe(self, source: str) -> bool:
        self.active_failsafes[source] = False

        if not any(self.active_failsafes.values()):
            self.current_state = FailSafeState.NORMAL
            self.speed_multiplier = 1.0
            logger.info("All fail-safes cleared, returning to normal operation")
            return True
        return False

    def emergency_stop(self, reason: str = "manual") -> None:
        logger.critical(f"EMERGENCY STOP triggered: {reason}")
        self.active_failsafes["emergency"] = True
        self.set_state(FailSafeState.EMERGENCY_STOP)
        self.speed_multiplier = 0.0

    def reset_emergency(self) -> None:
        self.active_failsafes["emergency"] = False
        self.clear_failsafe("emergency")

    def is_emergency_stopped(self) -> bool:
        return self.current_state == FailSafeState.EMERGENCY_STOP

    def get_speed_multiplier(self) -> float:
        return self.speed_multiplier

    def is_safe_for_movement(self) -> bool:
        return (
            self.current_state
            not in [
                FailSafeState.EMERGENCY_STOP,
                FailSafeState.SERVO_ERROR,
            ]
            and self.active_failsafes.get("imu", False) is False
        )

    def check_all_sensors(self) -> None:
        now = time.time()

        if not self.check_sensor_health("imu"):
            self.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)

        if not self.check_sensor_health("ultrasonic"):
            self.trigger_failsafe("ultrasonic", FailSafeState.ULTRASONIC_TIMEOUT)

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.current_state.value,
            "active_failsafes": self.active_failsafes,
            "speed_multiplier": self.speed_multiplier,
            "sensors": {
                name: {
                    "healthy": s.is_healthy,
                    "time_since_update": time.time() - s.last_update,
                    "failures": s.consecutive_failures,
                }
                for name, s in self.sensors.items()
            },
        }

    def get_health_report(self) -> Dict[str, Any]:
        status = self.get_status()
        overall_healthy = status["state"] == FailSafeState.NORMAL.value and not any(
            status["active_failsafes"].values()
        )

        issues = []
        for name, sensor_status in status["sensors"].items():
            if not sensor_status["healthy"]:
                issues.append(f"{name}_timeout")

        if status["active_failsafes"].get("imu"):
            issues.append("imu_failed")
        if status["active_failsafes"].get("ultrasonic"):
            issues.append("ultrasonic_failed")
        if status["active_failsafes"].get("vision"):
            issues.append("vision_dead")
        if status["active_failsafes"].get("servo"):
            issues.append("servo_error")
        if status["active_failsafes"].get("emergency"):
            issues.append("emergency_stop")

        return {
            "healthy": overall_healthy,
            "state": status["state"],
            "issues": issues,
            "speed_multiplier": status["speed_multiplier"],
        }
