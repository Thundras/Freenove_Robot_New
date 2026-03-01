import math
import time
from typing import Dict, Tuple, List

class LegOscillator:
    def __init__(self, phase_offset: float = 0.0):
        self.phase = phase_offset
        self.phase_offset = phase_offset
        self.idle_offset = 0.0
        
    def update_idle(self, t: float):
        """Subtle breathing motion: sine wave offset on Y"""
        self.idle_offset = math.sin(t * 2.0) * 2.0 # 2mm amplitude
        self.amplitude_x = 0.0
        self.amplitude_y = 0.0
        
    def reset(self, phase_offset: float):
        self.phase = phase_offset
        self.phase_offset = phase_offset

    def update(self, dt: float, speed: float):
        """Advance phase based on speed and time"""
        # speed is cycles per second (Hz)
        self.phase = (self.phase + speed * dt) % 1.0

    def get_coordinates(self, step_length: float, step_height: float, base_y: float) -> Tuple[float, float, float]:
        """
        Calculate local (x, y, z) for the leg tip based on phase.
        Phase 0.0 -> 0.5: Swing (lift and move forward)
        Phase 0.5 -> 1.0: Stance (push backward on ground)
        """
        x = 0.0
        y = base_y + self.idle_offset
        z = 0.0
        
        # Normalized phase within the semi-cycle
        if self.phase < 0.5:
            # Swing Phase
            swing_phase = self.phase / 0.5 # 0.0 to 1.0
            # x moves from -half_len to +half_len
            x = -step_length/2 + swing_phase * step_length
            # y lifts up and down (sinusoidal)
            y = base_y - math.sin(swing_phase * math.pi) * step_height
        else:
            # Stance Phase
            stance_phase = (self.phase - 0.5) / 0.5 # 0.0 to 1.0
            # x moves from +half_len back to -half_len
            x = step_length/2 - stance_phase * step_length
            # y stays at ground level
            y = base_y
            
        return x, y, z

class GaitSequencer:
    def __init__(self, base_height: float = 90.0):
        self.base_height = base_height
        self.current_speed = 0.0
        self.target_speed = 0.0
        self.turn_rate = 0.0 # -1.0 (Left) to 1.0 (Right)
        self.ramp_rate = 0.5 # acceleration per second
        self.pose_offset = 0.0 # Vertical offset for poses (e.g. submissive)
        self.rear_pose_offset = 0.0
        
        self.step_length = 40.0
        self.step_height = 20.0
        
        self.oscillators = {
            "fl": LegOscillator(0.0),
            "fr": LegOscillator(0.5),
            "rl": LegOscillator(0.5),
            "rr": LegOscillator(0.0)
        }
        self.set_gait("trot")

    def set_gait(self, gait_type: str):
        if gait_type.lower() == "trot":
            # Diagonal pairs
            self.oscillators["fl"].reset(0.0)
            self.oscillators["rr"].reset(0.0)
            self.oscillators["fr"].reset(0.5)
            self.oscillators["rl"].reset(0.5)
        elif gait_type.lower() == "walk":
            # Sequential
            self.oscillators["fl"].reset(0.0)
            self.oscillators["rr"].reset(0.25)
            self.oscillators["fr"].reset(0.5)
            self.oscillators["rl"].reset(0.75)

    def set_pose(self, pose_name: str):
        """Sets a specific body posture"""
        p = pose_name.lower()
        if p == "normal":
            self.pose_offset = 0.0
            self.rear_pose_offset = 0.0
        elif p == "submissive":
            self.pose_offset = -30.0
            self.rear_pose_offset = -30.0
        elif p == "sit":
            self.pose_offset = -10.0
            self.rear_pose_offset = -60.0
        elif p == "down":
            self.pose_offset = -60.0
            self.rear_pose_offset = -60.0
        elif p == "aggressive":
            self.pose_offset = 15.0
            self.rear_pose_offset = 15.0
        elif p == "playful":
            self.pose_offset = 15.0
            self.rear_pose_offset = -15.0

    def set_target_speed(self, speed: float, turn: float = 0.0):
        self.target_speed = speed
        self.turn_rate = turn

    def update(self, dt: float):
        # 1. Handle Ramping
        if self.current_speed < self.target_speed:
            self.current_speed = min(self.target_speed, self.current_speed + self.ramp_rate * dt)
        elif self.current_speed > self.target_speed:
            self.current_speed = max(self.target_speed, self.current_speed - self.ramp_rate * dt)
            
        # 2. Update Oscillators
        t = time.time()
        for osc in self.oscillators.values():
            osc.update(dt, self.current_speed)
            if self.current_speed < 0.01:
                osc.update_idle(t)
            else:
                osc.idle_offset = 0.0

    def get_phases(self) -> Dict[str, float]:
        return {name: osc.phase for name, osc in self.oscillators.items()}

    def calculate_step(self, t: float = 0.0) -> Dict[str, Tuple[float, float, float]]:
        """Returns target (x,y,z) for each leg"""
        coords = {}
        for name, osc in self.oscillators.items():
            # Apply different offsets for front vs rear to support 'sitting'
            offset = self.rear_pose_offset if name.startswith('r') else self.pose_offset
            effective_height = self.base_height + offset
            
            # --- ROTATION LOGIC ---
            # If turn_rate > 0 (Right), left legs move more forward, right legs move less or backward
            # This is a simplified "tank-like" rotation in the gait
            leg_speed_mod = 1.0
            if self.turn_rate != 0:
                if name.endswith('l'): # Left legs
                    leg_speed_mod = 1.0 + self.turn_rate
                else: # Right legs
                    leg_speed_mod = 1.0 - self.turn_rate
            
            # Scale step length per leg based on turn rate
            current_leg_step_len = self.step_length * leg_speed_mod
            
            coords[name] = osc.get_coordinates(current_leg_step_len, self.step_height, effective_height)
        return coords
