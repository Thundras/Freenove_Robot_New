import math
import time
from typing import Dict, Tuple, List

class LegOscillator:
    def __init__(self, phase_offset: float = 0.0, base_z: float = 23.0):
        self.phase = phase_offset
        self.phase_offset = phase_offset
        self.base_z = base_z
        self.idle_offset_x = 0.0
        self.idle_offset_y = 0.0
        self.idle_offset_z = 0.0
        
    def update_idle(self, t: float, leg_index: int = 0):
        """Organic breathing and swaying motion"""
        # Vertical breath (Y) - 3mm amplitude
        self.idle_offset_y = math.sin(t * 1.5 + leg_index * 0.2) * 3.0
        # Horizontal sway (X) - 2mm amplitude, different frequency
        self.idle_offset_x = math.cos(t * 0.8 + leg_index * 0.5) * 2.0
        # Subtle weight shift (Z)
        self.idle_offset_z = math.sin(t * 0.5 + leg_index) * 1.5
        
    def reset(self, phase_offset: float):
        self.phase = phase_offset
        self.phase_offset = phase_offset

    def update(self, dt: float, speed: float):
        """Advance phase based on speed and time"""
        # speed is cycles per second (Hz)
        self.phase = (self.phase + speed * dt) % 1.0

    def get_coordinates(self, step_length: float, step_height: float, base_y: float) -> Tuple[float, float, float]:
        """Calculate local (x, y, z) for the leg tip based on phase."""
        x = self.idle_offset_x
        y = base_y + self.idle_offset_y
        z = self.base_z + self.idle_offset_z
        
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
        self.current_gait = "trot"
        self.current_pose = "normal"
        self.set_gait("trot")

    def set_gait(self, gait_type: str):
        self.current_gait = gait_type.lower()
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
        self.current_pose = pose_name.lower()
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
        elif p == "calibrate":
            self.pose_offset = 43.0 # y=133 (90 + 23 shoulder + 20) ? No, let's just use max reach
            self.rear_pose_offset = 43.0
            self.current_speed = 0.0
            self.target_speed = 0.0
            # Zero out step length/height for true straight stand
            self.step_length = 0.0
            self.step_height = 0.0
            # Reset phases and idle offsets
            for name, osc in self.oscillators.items():
                osc.phase = 0.5 
                osc.idle_offset_x = 0.0
                osc.idle_offset_y = 0.0
                osc.idle_offset_z = 0.0
                # CRITICAL: For calibration, we want Z = 0 (vertical shoulder)
                osc.base_z = 0.0 
        else:
            # Restore default base_z for other poses
            for osc in self.oscillators.values():
                osc.base_z = 23.0

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
        for i, (name, osc) in enumerate(self.oscillators.items()):
            osc.update(dt, self.current_speed)
            if self.current_speed < 0.01 and self.current_pose != "calibrate":
                osc.update_idle(t, i)
            else:
                osc.idle_offset_x = 0.0
                osc.idle_offset_y = 0.0
                osc.idle_offset_z = 0.0

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
