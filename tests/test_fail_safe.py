import pytest
import time
from utils.fail_safe import FailSafeManager, FailSafeState, FailSafeConfig, SensorHealth


class TestFailSafeManager:
    def test_initial_state(self):
        fs = FailSafeManager()
        assert fs.current_state == FailSafeState.NORMAL
        assert fs.speed_multiplier == 1.0

    def test_update_heartbeat(self):
        fs = FailSafeManager()
        fs.update_sensor_heartbeat("imu")
        assert fs.sensors["imu"].is_healthy is True
        assert fs.sensors["imu"].consecutive_failures == 0

    def test_check_sensor_health_healthy(self):
        fs = FailSafeManager()
        fs.update_sensor_heartbeat("imu")
        result = fs.check_sensor_health("imu")
        assert result is True

    def test_check_sensor_health_timeout_consecutive(self):
        fs = FailSafeManager()
        fs.sensors["imu"].last_update = time.time() - 5.0
        for _ in range(3):
            result = fs.check_sensor_health("imu")
        assert result is False

    def test_trigger_failsafe_imu(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)
        assert fs.active_failsafes["imu"] is True
        assert fs.current_state == FailSafeState.IMU_TIMEOUT
        assert fs.speed_multiplier == 0.0

    def test_trigger_failsafe_ultrasonic(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("ultrasonic", FailSafeState.ULTRASONIC_TIMEOUT)
        assert fs.active_failsafes["ultrasonic"] is True
        assert fs.current_state == FailSafeState.ULTRASONIC_TIMEOUT
        assert fs.speed_multiplier == 0.5

    def test_clear_failsafe(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)
        result = fs.clear_failsafe("imu")
        assert result is True
        assert fs.current_state == FailSafeState.NORMAL
        assert fs.speed_multiplier == 1.0

    def test_clear_partial_failsafe(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)
        fs.trigger_failsafe("ultrasonic", FailSafeState.ULTRASONIC_TIMEOUT)
        fs.clear_failsafe("imu")
        assert fs.current_state == FailSafeState.ULTRASONIC_TIMEOUT
        assert fs.speed_multiplier == 0.5

    def test_is_safe_for_movement_normal(self):
        fs = FailSafeManager()
        assert fs.is_safe_for_movement() is True

    def test_is_safe_for_movement_imu_failed(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)
        assert fs.is_safe_for_movement() is False

    def test_is_safe_for_movement_emergency_stop(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("servo", FailSafeState.EMERGENCY_STOP)
        assert fs.is_safe_for_movement() is False

    def test_get_speed_multiplier_normal(self):
        fs = FailSafeManager()
        assert fs.get_speed_multiplier() == 1.0

    def test_get_speed_multiplier_ultrasonic_failsafe(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("ultrasonic", FailSafeState.ULTRASONIC_TIMEOUT)
        assert fs.get_speed_multiplier() == 0.5

    def test_get_status(self):
        fs = FailSafeManager()
        status = fs.get_status()
        assert "state" in status
        assert "active_failsafes" in status
        assert "speed_multiplier" in status
        assert "sensors" in status

    def test_check_all_sensors(self):
        fs = FailSafeManager()
        fs.sensors["imu"].last_update = time.time() - 5.0
        for _ in range(3):
            fs.check_all_sensors()
        assert fs.current_state == FailSafeState.IMU_TIMEOUT

    def test_unknown_sensor_returns_true(self):
        fs = FailSafeManager()
        result = fs.check_sensor_health("unknown_sensor")
        assert result is True


class TestFailSafeConfig:
    def test_default_config(self):
        config = FailSafeConfig()
        assert config.imu_timeout == 2.0
        assert config.ultrasonic_timeout == 1.0
        assert config.max_consecutive_failures == 3

    def test_custom_config(self):
        config = FailSafeConfig(imu_timeout=5.0, speed_reduction_factor=0.3)
        assert config.imu_timeout == 5.0
        assert config.speed_reduction_factor == 0.3


class TestSensorHealth:
    def test_sensor_health_creation(self):
        sensor = SensorHealth("test", time.time(), 2.0)
        assert sensor.name == "test"
        assert sensor.is_healthy is True
        assert sensor.consecutive_failures == 0


class TestEmergencyStop:
    def test_emergency_stop_initial_state(self):
        fs = FailSafeManager()
        assert fs.is_emergency_stopped() is False
        assert fs.current_state == FailSafeState.NORMAL

    def test_emergency_stop_trigger(self):
        fs = FailSafeManager()
        fs.emergency_stop("test_reason")
        assert fs.is_emergency_stopped() is True
        assert fs.current_state == FailSafeState.EMERGENCY_STOP
        assert fs.speed_multiplier == 0.0
        assert fs.active_failsafes.get("emergency") is True

    def test_emergency_stop_blocks_movement(self):
        fs = FailSafeManager()
        fs.emergency_stop()
        assert fs.is_safe_for_movement() is False

    def test_emergency_reset(self):
        fs = FailSafeManager()
        fs.emergency_stop()
        fs.reset_emergency()
        assert fs.is_emergency_stopped() is False
        assert fs.current_state == FailSafeState.NORMAL

    def test_emergency_stop_preserves_other_failsafes(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)
        fs.emergency_stop()
        assert fs.active_failsafes.get("imu") is True
        assert fs.active_failsafes.get("emergency") is True
        assert fs.is_emergency_stopped() is True

    def test_emergency_stop_with_custom_reason(self):
        fs = FailSafeManager()
        fs.emergency_stop("button_pressed")
        assert fs.is_emergency_stopped() is True


class TestHealthMonitoring:
    def test_health_report_normal(self):
        fs = FailSafeManager()
        report = fs.get_health_report()
        assert report["healthy"] is True
        assert report["issues"] == []
        assert report["state"] == "normal"

    def test_health_report_with_issues(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)
        report = fs.get_health_report()
        assert report["healthy"] is False
        assert "imu_failed" in report["issues"]

    def test_health_report_emergency_stop(self):
        fs = FailSafeManager()
        fs.emergency_stop()
        report = fs.get_health_report()
        assert report["healthy"] is False
        assert "emergency_stop" in report["issues"]
        assert report["state"] == "emergency_stop"

    def test_health_report_multiple_issues(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)
        fs.trigger_failsafe("ultrasonic", FailSafeState.ULTRASONIC_TIMEOUT)
        fs.emergency_stop()
        report = fs.get_health_report()
        assert report["healthy"] is False
        assert len(report["issues"]) >= 3
        assert "imu_failed" in report["issues"]
        assert "ultrasonic_failed" in report["issues"]
        assert "emergency_stop" in report["issues"]

    def test_health_report_speed_multiplier(self):
        fs = FailSafeManager()
        report = fs.get_health_report()
        assert report["speed_multiplier"] == 1.0

        fs.trigger_failsafe("ultrasonic", FailSafeState.ULTRASONIC_TIMEOUT)
        report = fs.get_health_report()
        assert report["speed_multiplier"] == 0.5


class TestGracefulDegradation:
    def test_available_features_normal(self):
        fs = FailSafeManager()
        features = fs.get_available_features()
        assert features["movement"] is True
        assert features["vision"] is True
        assert features["face_recognition"] is True
        assert features["obstacle_avoidance"] is True
        assert features["stabilization"] is True
        assert features["autonomous_mode"] is True

    def test_available_features_imu_failed(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)
        features = fs.get_available_features()
        assert features["movement"] is False
        assert features["stabilization"] is False
        assert features["autonomous_mode"] is False

    def test_available_features_vision_failed(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("vision", FailSafeState.VISION_DEAD)
        features = fs.get_available_features()
        assert features["movement"] is True
        assert features["vision"] is False
        assert features["face_recognition"] is False
        assert features["autonomous_mode"] is False

    def test_available_features_ultrasonic_failed(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("ultrasonic", FailSafeState.ULTRASONIC_TIMEOUT)
        features = fs.get_available_features()
        assert features["obstacle_avoidance"] is False
        assert features["autonomous_mode"] is True

    def test_degraded_mode_normal(self):
        fs = FailSafeManager()
        assert fs.get_degraded_mode() == "normal"

    def test_degraded_mode_imu_failed(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)
        assert fs.get_degraded_mode() == "no_stabilization"

    def test_degraded_mode_emergency(self):
        fs = FailSafeManager()
        fs.emergency_stop()
        assert fs.get_degraded_mode() == "emergency_stop"

    def test_degraded_mode_vision(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("vision", FailSafeState.VISION_DEAD)
        assert fs.get_degraded_mode() == "blind_mode"

    def test_is_autonomous_allowed_normal(self):
        fs = FailSafeManager()
        assert fs.is_autonomous_allowed() is True

    def test_is_autonomous_allowed_vision_failed(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("vision", FailSafeState.VISION_DEAD)
        assert fs.is_autonomous_allowed() is False

    def test_is_autonomous_allowed_imu_failed(self):
        fs = FailSafeManager()
        fs.trigger_failsafe("imu", FailSafeState.IMU_TIMEOUT)
        assert fs.is_autonomous_allowed() is False
