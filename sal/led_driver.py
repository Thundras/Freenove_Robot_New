import logging
from .base import ISensor
from utils.config import ConfigManager
import math
import time

try:
    import board
    import neopixel
except ImportError:
    board = None

logger = logging.getLogger(__name__)

class LedDriver:
    """
    Driver for WS2812 (NeoPixel) LEDs.
    """
    def __init__(self, config: ConfigManager):
        self.config = config
        self.num_pixels = config.get("hardware.led_count", 8)
        self.pin_id = config.get("hardware.led_pin", 18)
        
        # Map pin ID to board attribute (e.g. 18 -> board.D18)
        self.pin = getattr(board, f"D{self.pin_id}") if board else None
        
        if board is None:
            raise ImportError("Adafruit libraries not found.")

        try:
            self.pixels = neopixel.NeoPixel(self.pin, self.num_pixels, brightness=0.5, auto_write=False)
            self.current_state = {"pattern": "off", "color": [0, 0, 0], "pixels": [[0,0,0]] * self.num_pixels}
            logger.info(f"NeoPixel initialized on Pin {self.pin} with {self.num_pixels} LEDs.")
        except Exception as e:
            logger.error(f"Failed to initialize NeoPixel: {e}")
            raise

    def set_color(self, index: int, r: int, g: int, b: int):
        if 0 <= index < self.num_pixels:
            self.pixels[index] = (r, g, b)
            self.current_state = {"pattern": "manual", "color": [r, g, b]}

    def show(self):
        # Sync pixel data to current_state for the dashboard
        self.current_state["pixels"] = [list(p) for p in self.pixels]
        self.pixels.show()

    def clear(self):
        self.pixels.fill((0, 0, 0))
        self.current_state = {"pattern": "off", "color": [0, 0, 0]}
        self.show()

    def animate(self, pattern: str, color: tuple, speed: float = 1.0):
        """
        Executes a procedural animation pattern.
        pattern: 'spin', 'breathe', 'scanner', 'blink'
        color: (r, g, b)
        """
        self.current_state = {"pattern": pattern, "color": list(color)}
        t = time.time() * speed
        r, g, b = color

        if pattern == "spin":
            # One pixel rotates around the 7-pixel ring
            index = int(t * 7) % 7
            self.pixels.fill((0, 0, 0))
            self.pixels[index] = color
            # Add a little trail
            self.pixels[(index - 1) % 7] = (r//4, g//4, b//4)
            
        elif pattern == "breathe":
            # All pixels fade in and out
            brightness = (math.sin(t * 3.0) + 1) / 2
            self.pixels.fill((int(r * brightness), int(g * brightness), int(b * brightness)))
            
        elif pattern == "scanner":
            # Knight Rider style back and forth
            # Ring is 0-6. Middle is 0? Or 0-6 around.
            # For a 7-ring (usually 1 center, 6 around), 0 is center? 
            # Freenove ring: usually 0 is center, 1-6 are around.
            pos = int((math.sin(t * 5.0) + 1) / 2 * 6) + 1
            self.pixels.fill((0, 0, 0))
            self.pixels[pos] = color
            self.pixels[0] = (r//4, g//4, b//4) # Dim center
            
        elif pattern == "heartbeat":
            # Quick double pulse
            phase = t % 2.0
            brightness = 0.0
            if phase < 0.2: brightness = phase / 0.2
            elif phase < 0.4: brightness = 1.0 - (phase-0.2)/0.2
            elif phase < 0.6: brightness = (phase-0.4)/0.2
            elif phase < 0.8: brightness = 1.0 - (phase-0.6)/0.2
            
            self.pixels.fill((int(r * brightness), int(g * brightness), int(b * brightness)))

        self.show()
