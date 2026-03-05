import time
import logging

logger = logging.getLogger(__name__)

class MoodManager:
    """
    Manages internal emotional/biological states of the robot.
    Values are 0.0 (None) to 1.0 (Max).
    """
    def __init__(self):
        self.moods = {
            "energy": 1.0,      # Tiredness (biological clock)
            "excitement": 0.5,  # Playfulness / Curiosity
            "comfort": 0.8,     # Social trust / Anxiety
            "aggression": 0.0   # Defensiveness
        }
        self.last_update = time.time()

    def update(self, dt: float):
        # 1. Energy Decay (Biological drain)
        # Slow drain over 2 hours = 1.0 / 7200 per second
        self.moods["energy"] = max(0.0, self.moods["energy"] - dt / 7200.0)
        
        # 2. Base Mood Normalization (Emotions return to baseline)
        baseline = {"excitement": 0.3, "comfort": 0.7, "aggression": 0.0}
        recovery_speed = 0.005 # Units per second
        
        for m, base in baseline.items():
            if self.moods[m] > base:
                self.moods[m] = max(base, self.moods[m] - recovery_speed * dt)
            elif self.moods[m] < base:
                self.moods[m] = min(base, self.moods[m] + recovery_speed * dt)

    def adjust(self, mood: str, delta: float):
        if mood in self.moods:
            self.moods[mood] = max(0.0, min(1.0, self.moods[mood] + delta))
            
    def get(self, mood: str) -> float:
        return self.moods.get(mood, 0.0)
