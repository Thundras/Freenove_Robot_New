import pytest
import time
from utils.led_animations import (
    LEDAnimationManager,
    LEDPattern,
    LEDAction,
    LEDConfig,
)


class MockLED:
    def __init__(self, num_pixels=7):
        self.num_pixels = num_pixels
        self.pixels = [[0, 0, 0]] * num_pixels
        self.show_called = False

    def set_color(self, index, r, g, b):
        if 0 <= index < self.num_pixels:
            self.pixels[index] = [r, g, b]
        self.show_called = False

    def fill(self, r, g, b):
        self.pixels = [[r, g, b]] * self.num_pixels
        self.show_called = True

    def clear(self):
        self.pixels = [[0, 0, 0]] * self.num_pixels
        self.show_called = True

    def show(self):
        self.show_called = True


class TestLEDAnimationManager:
    def test_initialization(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        assert manager.current_pattern == LEDPattern.OFF
        assert manager.current_action == LEDAction.IDLE
        assert manager.num_pixels == 7

    def test_set_pattern_off(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_pattern(LEDPattern.OFF)
        assert manager.current_pattern == LEDPattern.OFF

    def test_set_pattern_solid(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_pattern(LEDPattern.SOLID, (255, 0, 0))
        assert manager.current_pattern == LEDPattern.SOLID
        assert mock_led.pixels[0] == [255, 0, 0]

    def test_set_color(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_color(100, 150, 200)
        assert mock_led.pixels[0] == [100, 150, 200]

    def test_set_pixel(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_pixel(3, 255, 255, 255)
        assert mock_led.pixels[3] == [255, 255, 255]
        assert mock_led.pixels[0] == [0, 0, 0]

    def test_set_action_idle(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_action(LEDAction.IDLE)
        assert manager.current_action == LEDAction.IDLE

    def test_set_action_moving(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_action(LEDAction.MOVING)
        assert manager.current_action == LEDAction.MOVING
        assert manager.current_pattern == LEDPattern.CHASE

    def test_set_action_alert(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_action(LEDAction.ALERT)
        assert manager.current_action == LEDAction.ALERT
        assert manager.current_pattern == LEDPattern.FLASH

    def test_set_action_happy(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_action(LEDAction.HAPPY)
        assert manager.current_action == LEDAction.HAPPY
        assert manager.current_pattern == LEDPattern.RAINBOW

    def test_update_breathe(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_pattern(LEDPattern.BREATHE, (0, 100, 200))
        manager.update(0.5)
        manager.update(0.5)
        assert mock_led.show_called is True

    def test_update_chase(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_pattern(LEDPattern.CHASE, (0, 255, 0))
        manager.update(0.1)
        assert mock_led.show_called is True

    def test_update_rainbow(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_pattern(LEDPattern.RAINBOW)
        manager.update(0.1)
        assert mock_led.show_called is True

    def test_update_flash(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_pattern(LEDPattern.FLASH, (255, 0, 0))
        manager.update(0.1)
        manager.update(0.1)
        manager.update(0.1)
        manager.update(0.1)
        assert mock_led.show_called is True

    def test_get_status(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        status = manager.get_status()
        assert "pattern" in status
        assert "action" in status
        assert "color" in status
        assert "speed" in status
        assert "num_pixels" in status

    def test_set_speed(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_speed(2.0)
        assert manager.speed == 2.0

    def test_set_speed_clamp(self):
        mock_led = MockLED()
        manager = LEDAnimationManager(mock_led)
        manager.set_speed(20.0)
        assert manager.speed == 10.0
        manager.set_speed(0.01)
        assert manager.speed == 0.1

    def test_hsv_to_rgb(self):
        r, g, b = LEDAnimationManager._hsv_to_rgb(0, 1.0, 1.0)
        assert r == 255 and g == 0 and b == 0
        r, g, b = LEDAnimationManager._hsv_to_rgb(120, 1.0, 1.0)
        assert r == 0 and g == 255 and b == 0
        r, g, b = LEDAnimationManager._hsv_to_rgb(240, 1.0, 1.0)
        assert r == 0 and g == 0 and b == 255


class TestLEDPattern:
    def test_pattern_values(self):
        assert LEDPattern.OFF.value == "off"
        assert LEDPattern.SOLID.value == "solid"
        assert LEDPattern.PULSE.value == "pulse"
        assert LEDPattern.RAINBOW.value == "rainbow"
        assert LEDPattern.CHASE.value == "chase"
        assert LEDPattern.BREATHE.value == "breathe"
        assert LEDPattern.FLASH.value == "flash"


class TestLEDAction:
    def test_action_values(self):
        assert LEDAction.IDLE.value == "idle"
        assert LEDAction.MOVING.value == "moving"
        assert LEDAction.ALERT.value == "alert"
        assert LEDAction.HAPPY.value == "happy"
        assert LEDAction.ERROR.value == "error"
        assert LEDAction.CHARGING.value == "charging"
        assert LEDAction.SLEEPING.value == "sleeping"


class TestLEDConfig:
    def test_default_config(self):
        config = LEDConfig()
        assert config.num_pixels == 7
        assert config.default_color == (0, 255, 0)
        assert config.animation_speed == 1.0

    def test_custom_config(self):
        config = LEDConfig(
            num_pixels=10, default_color=(255, 0, 0), animation_speed=2.0
        )
        assert config.num_pixels == 10
        assert config.default_color == (255, 0, 0)
        assert config.animation_speed == 2.0
