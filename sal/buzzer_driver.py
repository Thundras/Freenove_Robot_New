import logging
import time
try:
    from gpiozero import Buzzer
except ImportError:
    Buzzer = None

logger = logging.getLogger(__name__)

class BuzzerDriver:
    def __init__(self, config):
        self.config = config
        self.pin = config.get("hardware.buzzer_pin", 17)
        self.buzzer = None
        
        if Buzzer is None:
            raise ImportError("gpiozero not found")
            
        try:
            self.buzzer = Buzzer(self.pin)
            logger.info(f"BuzzerDriver initialized on Pin {self.pin}")
        except Exception as e:
            logger.error(f"Failed to init Buzzer: {e}")
            raise

    def beep(self, duration: float = 0.1):
        if self.buzzer:
            self.buzzer.on()
            time.sleep(duration)
            self.buzzer.off()

    def on(self):
        if self.buzzer:
            self.buzzer.on()

    def off(self):
        if self.buzzer:
            self.buzzer.off()
