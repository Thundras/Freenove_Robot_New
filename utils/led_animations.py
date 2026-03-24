import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LEDPattern(Enum):
    OFF = "off"
    SOLID = "solid"
    PULSE = "pulse"
    RAINBOW = "rainbow"
    CHASE = "chase"
    BREATHE = "breathe"
    FLASH = "flash"
    RANDOM = "random"


class LEDAction(Enum):
    IDLE = "idle"
    MOVING = "moving"
    ALERT = "alert"
    HAPPY = "happy"
    ERROR = "error"
    CHARGING = "charging"
    SLEEPING = "sleeping"


@dataclass
class LEDConfig:
    num_pixels: int = 7
    default_color: Tuple[int, int, int] = (0, 255, 0)
    animation_speed: float = 1.0


class LEDAnimationManager:
    def __init__(self, led_driver: Any, config: Optional[Any] = None):
        self.led = led_driver
        if config is None:
            self.config = LEDConfig()
        elif isinstance(config, LEDConfig):
            self.config = config
        else:
            self.config = LEDConfig(
                num_pixels=config.get("hardware.led_count", 7),
                default_color=tuple(config.get("led.default_color", [0, 255, 0])),
                animation_speed=config.get("led.animation_speed", 1.0),
            )
        self.num_pixels = self.config.num_pixels

        self.current_pattern = LEDPattern.OFF
        self.current_action = LEDAction.IDLE
        self.current_color = list(self.config.default_color)
        self.speed = self.config.animation_speed

        self._animation_time = 0.0
        self._frame_index = 0

        self.action_patterns: Dict[
            LEDAction, Tuple[LEDPattern, Tuple[int, int, int]]
        ] = {
            LEDAction.IDLE: (LEDPattern.BREATHE, (0, 50, 255)),
            LEDAction.MOVING: (LEDPattern.CHASE, (0, 255, 0)),
            LEDAction.ALERT: (LEDPattern.FLASH, (255, 0, 0)),
            LEDAction.HAPPY: (LEDPattern.RAINBOW, (255, 255, 0)),
            LEDAction.ERROR: (LEDPattern.FLASH, (255, 0, 0)),
            LEDAction.CHARGING: (LEDPattern.PULSE, (0, 255, 100)),
            LEDAction.SLEEPING: (LEDPattern.OFF, (0, 0, 0)),
        }

        logger.info(f"LEDAnimationManager initialized with {self.num_pixels} pixels")

    def set_action(self, action: LEDAction) -> None:
        if action != self.current_action:
            self.current_action = action
            if action in self.action_patterns:
                pattern, color = self.action_patterns[action]
                self.set_pattern(pattern, color)
            logger.debug(f"LED action changed to: {action.value}")

    def set_pattern(
        self, pattern: LEDPattern, color: Tuple[int, int, int] = None
    ) -> None:
        self.current_pattern = pattern
        if color:
            self.current_color = list(color)
        self._frame_index = 0
        self._animation_time = 0.0

        if pattern == LEDPattern.OFF:
            self.led.clear()
        elif pattern == LEDPattern.SOLID:
            self.led.fill(*self.current_color)
            self.led.show()
        logger.debug(f"LED pattern set to: {pattern.value}")

    def set_color(self, r: int, g: int, b: int) -> None:
        self.current_color = [r, g, b]
        self.led.fill(r, g, b)
        self.led.show()

    def set_pixel(self, index: int, r: int, g: int, b: int) -> None:
        self.led.set_color(index, r, g, b)
        self.led.show()

    def update(self, dt: float) -> None:
        self._animation_time += dt * self.speed

        if self.current_pattern == LEDPattern.PULSE:
            self._update_pulse()
        elif self.current_pattern == LEDPattern.CHASE:
            self._update_chase()
        elif self.current_pattern == LEDPattern.BREATHE:
            self._update_breathe()
        elif self.current_pattern == LEDPattern.RAINBOW:
            self._update_rainbow()
        elif self.current_pattern == LEDPattern.FLASH:
            self._update_flash()

    def _update_pulse(self) -> None:
        intensity = (abs(self._animation_time % 2.0 - 1.0)) * 255
        r = int(self.current_color[0] * intensity / 255)
        g = int(self.current_color[1] * intensity / 255)
        b = int(self.current_color[2] * intensity / 255)
        self.led.fill(r, g, b)
        self.led.show()

    def _update_chase(self) -> None:
        self._frame_index = int(self._animation_time * 4) % self.num_pixels
        self.led.clear()
        for i in range(3):
            idx = (self._frame_index + i) % self.num_pixels
            self.led.set_color(idx, *self.current_color)
        self.led.show()

    def _update_breathe(self) -> None:
        intensity = abs(self._animation_time % 4.0 - 2.0) / 2.0
        r = int(self.current_color[0] * intensity)
        g = int(self.current_color[1] * intensity)
        b = int(self.current_color[2] * intensity)
        self.led.fill(r, g, b)
        self.led.show()

    def _update_rainbow(self) -> None:
        self._frame_index = int(self._animation_time * 30) % 360
        for i in range(self.num_pixels):
            hue = (self._frame_index + i * 30) % 360
            r, g, b = self._hsv_to_rgb(hue, 1.0, 1.0)
            self.led.set_color(i, r, g, b)
        self.led.show()

    def _update_flash(self) -> None:
        if int(self._animation_time * 4) % 2 == 0:
            self.led.fill(*self.current_color)
        else:
            self.led.clear()
        self.led.show()

    @staticmethod
    def _hsv_to_rgb(h: int, s: float, v: float) -> Tuple[int, int, int]:
        import math

        if s == 0.0:
            return int(v * 255), int(v * 255), int(v * 255)
        i = int(h / 60.0) % 6
        f = h / 60.0 - i
        p = v * (1.0 - s)
        q = v * (1.0 - f * s)
        t = v * (1.0 - (1.0 - f) * s)
        if i == 0:
            return int(v * 255), int(t * 255), int(p * 255)
        elif i == 1:
            return int(q * 255), int(v * 255), int(p * 255)
        elif i == 2:
            return int(p * 255), int(v * 255), int(t * 255)
        elif i == 3:
            return int(p * 255), int(q * 255), int(v * 255)
        elif i == 4:
            return int(t * 255), int(p * 255), int(v * 255)
        else:
            return int(v * 255), int(p * 255), int(q * 255)

    def get_status(self) -> Dict[str, Any]:
        return {
            "pattern": self.current_pattern.value,
            "action": self.current_action.value,
            "color": self.current_color,
            "speed": self.speed,
            "num_pixels": self.num_pixels,
        }

    def set_speed(self, speed: float) -> None:
        self.speed = max(0.1, min(10.0, speed))
