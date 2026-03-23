import pytest
from unittest.mock import Mock, patch, MagicMock
from sal.mock_drivers import MockBattery
from utils.config import ConfigManager

# Mock smbus before importing battery_driver
import sys

sys.modules["smbus"] = Mock()


class TestBatteryProtection:
    """Tests for battery low-voltage protection."""

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "hardware.i2c_bus": 1,
            "hardware.ads7830_address": 0x48,
            "battery.voltage_min": 7.0,
            "battery.voltage_max": 8.4,
            "battery.voltage_low": 7.2,
            "battery.voltage_critical": 6.8,
        }.get(key, default)
        return config

    def test_battery_driver_has_voltage_threshold_from_config(self, mock_config):
        """BatteryDriver should read voltage thresholds from config."""
        from sal.battery_driver import BatteryDriver

        driver = BatteryDriver(mock_config)
        assert driver.voltage_low == 7.2
        assert driver.voltage_min == 7.0
        assert driver.voltage_max == 8.4

    def test_battery_driver_has_is_critical_method(self, mock_config):
        """BatteryDriver should have is_critical method."""
        from sal.battery_driver import BatteryDriver

        driver = BatteryDriver(mock_config)
        assert hasattr(driver, "is_critical")
        assert callable(driver.is_critical)

    def test_is_critical_returns_false_above_threshold(self, mock_config):
        """is_critical should return False when voltage is above threshold."""
        from sal.battery_driver import BatteryDriver

        driver = BatteryDriver(mock_config)
        driver.data.voltage = 7.0
        assert driver.is_critical() is False

    def test_is_critical_returns_true_below_threshold(self, mock_config):
        """is_critical should return True when voltage is below threshold."""
        from sal.battery_driver import BatteryDriver

        driver = BatteryDriver(mock_config)
        driver.data.voltage = 6.5
        assert driver.is_critical() is True


class TestBatteryProtectionConfig:
    """Tests for battery protection configuration."""

    def test_default_config_has_battery_section(self):
        """Default config should have battery section."""
        config = ConfigManager("config/config.yaml")
        battery = config.get("battery", {})
        assert "voltage_min" in battery
        assert "voltage_max" in battery
        assert "voltage_low" in battery

    def test_config_voltage_thresholds(self):
        """Config should have reasonable voltage thresholds."""
        config = ConfigManager("config/config.yaml")
        battery = config.get("battery", {})

        assert battery["voltage_min"] < battery["voltage_low"]
        assert battery["voltage_low"] < battery["voltage_max"]
        assert battery["voltage_max"] <= 8.5

    def test_config_low_warning_interval(self):
        """Config should have warning interval."""
        config = ConfigManager("config/config.yaml")
        battery = config.get("battery", {})

        assert "low_warning_interval" in battery
        assert battery["low_warning_interval"] > 0


class TestMockBattery:
    """Tests for MockBattery low voltage behavior."""

    def test_mock_battery_has_is_low(self):
        """MockBattery should track is_low status."""
        battery = MockBattery()
        data = battery.get_data()
        assert hasattr(data, "is_low")

    def test_mock_battery_default_not_low(self):
        """MockBattery should not be low by default."""
        battery = MockBattery()
        data = battery.get_data()
        assert data.is_low is False

    def test_mock_battery_percentage_in_range(self):
        """MockBattery percentage should be 0-100."""
        battery = MockBattery()
        data = battery.get_data()
        assert 0 <= data.percentage <= 100
