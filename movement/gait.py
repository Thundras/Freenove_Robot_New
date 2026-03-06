import math
import time
import numpy as np
from typing import Dict, Tuple, List

class LegOscillator:
    def __init__(self, phase_offset: float = 0.0, base_x: float = 0.0, base_z: float = 0.0):
        self.phase = phase_offset
        self.phase_offset = phase_offset
        self.target_phase_offset = phase_offset
        self.blending_speed = 1.2 # Hz (how fast to shift rhythm)
        self.base_x = base_x
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
        # 1. Smoothly interpolate phase_offset (the rhythm)
        if abs(self.phase_offset - self.target_phase_offset) > 0.001:
            diff = self.target_phase_offset - self.phase_offset
            # Fix wrapping (e.g. 0.1 to 0.9 should go backwards or vice versa)
            if diff > 0.5: diff -= 1.0
            elif diff < -0.5: diff += 1.0
            self.phase_offset = (self.phase_offset + diff * self.blending_speed * dt) % 1.0

        # 2. Advance actual phase
        # speed is cycles per second (Hz)
        self.phase = (self.phase + speed * dt) % 1.0

    def get_coordinates(self, step_length: float, step_height: float, base_y: float) -> Tuple[float, float, float]:
        """Calculate local (x, y, z) for the leg tip relative to shoulder."""
        # Use the CURRENT phase adjusted by the CURRENT phase_offset
        effective_phase = (self.phase + self.phase_offset) % 1.0
        
        x = self.idle_offset_x
        y = base_y + self.idle_offset_y
        z = self.base_z + self.idle_offset_z
        
        # Normalized phase within the semi-cycle
        if effective_phase < 0.5:
            # Swing Phase
            swing_phase = effective_phase / 0.5 # 0.0 to 1.0
            x += -step_length/2 + swing_phase * step_length
            y -= math.sin(swing_phase * math.pi) * step_height
        else:
            # Stance Phase
            stance_phase = (effective_phase - 0.5) / 0.5 # 0.0 to 1.0
            x += step_length/2 - stance_phase * step_length
            
        return x, y, z

class GaitSequencer:
    def __init__(self, base_height: float = 75.0):
        self.base_height = base_height # Vertical distance from shoulder to foot tip
        self.shoulder_to_body_offset = 50.0 # From belly bottom to shoulder joint
        
        self.current_speed = 0.0
        self.target_speed = 0.0
        self.turn_rate = 0.0 # -1.0 (Left) to 1.0 (Right)
        self.ramp_rate = 0.5 # acceleration per second
        
        # 6-DOF Body State (Target vs Current for smoothing)
        self.target_body_pose = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0, "x": 0.0, "y": 0.0, "z": 0.0}
        self.current_body_pose = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0, "x": 0.0, "y": 0.0, "z": 0.0}
        self.auto_com_x = 0.0 # Automatic CoM shift (Pitch)
        self.auto_com_z = 0.0 # Automatic CoM shift (Roll)
        self.auto_lean = 0.0 # Lean into turn (Roll)
        self.look_at_yaw = 0.0 # Body gaze offset
        self.look_at_pitch = 0.0 # Body gaze offset
        self.stab_roll = 0.0 # IMU Stabilization Offset
        self.stab_pitch = 0.0 # IMU Stabilization Offset
        
        # DNA Layer Stacking
        self.additive_layers: Dict[str, Dict[str, float]] = {} # e.g. {"Breathing": {"y": 2.0}}
        
        self.smoothing_speed = 3.0 # Rad or mm per second
        
        self.step_length = 40.0
        self.step_height = 20.0
        
        self.oscillators = {
            "fl": LegOscillator(0.0, base_x=70.0, base_z=-40.0),
            "fr": LegOscillator(0.0, base_x=70.0, base_z=40.0),
            "rl": LegOscillator(0.0, base_x=-70.0, base_z=-40.0),
            "rr": LegOscillator(0.0, base_x=-70.0, base_z=40.0)
        }
        self.current_gait = "idle"
        # Gait Definitions (Phase offsets)
        self.gaits = {
            "idle": {"fl":0.0, "fr":0.0, "rl":0.0, "rr":0.0},
            "walk": {"fl":0.0, "fr":0.5, "rl":0.75, "rr":0.25}, # 4-beat
            "trot": {"fl":0.0, "fr":0.5, "rl":0.5, "rr":0.0}   # 2-beat diagonal
        }
        self._apply_gait("idle")
        self.current_pose = "normal"
        self._apply_gait("idle")

    def set_base_height(self, height: float):
        """Sets the height of the belly from the ground. 
        IK y = height + shoulder_to_body_offset"""
        self.base_height = height + self.shoulder_to_body_offset

    def _apply_gait(self, gait_name: str):
        if gait_name in self.gaits:
            offsets = self.gaits[gait_name]
            for leg, offset in offsets.items():
                self.oscillators[leg].target_phase_offset = offset
            self.current_gait = gait_name

    def set_pose(self, pose_name: str):
        """Sets a target body posture (Smoothing handles the transition)"""
        self.current_pose = pose_name.lower()
        p = pose_name.lower()
        # Reset targets to neutral first
        target = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0, "x": 0.0, "y": 0.0, "z": 0.0}
        
        if p == "normal":
            pass # Neutral
        elif p == "submissive":
            target["pitch"] = 10.0 # Degrees
            target["y"] = -30.0
        elif p == "sit":
            target["pitch"] = 25.0
            target["y"] = -40.0
            target["x"] = -10.0
        elif p == "down":
            target["y"] = -60.0
        elif p == "aggressive":
            target["pitch"] = -15.0
            target["y"] = 15.0
        elif p == "playful":
            target["pitch"] = -10.0
            target["roll"] = 15.0
            target["y"] = 0.0
        elif p == "calibrate":
            self.current_speed = 0.0
            self.target_speed = 0.0
            self.step_length = 0.0
            self.step_height = 0.0
            for osc in self.oscillators.values():
                osc.phase = 0.0
                osc.idle_offset_x = 0.0
                osc.idle_offset_y = 0.0
                osc.idle_offset_z = 0.0
        
        self.target_body_pose = target

    def set_target_speed(self, speed: float, turn: float = 0.0):
        self.target_speed = speed
        self.turn_rate = turn

    def update_body_pose(self, key: str, value: float):
        """Updates a specific component of the target body pose (roll, pitch, yaw, x, y, z)"""
        if key in self.target_body_pose:
            self.target_body_pose[key] = value

    def set_look_at(self, yaw: float, pitch: float):
        """Sets expressive body gaze offsets (additive)"""
        self.look_at_yaw = yaw
        self.look_at_pitch = pitch

    def add_additive_layer(self, layer_name: str, params: Dict[str, float]):
        """Adds or updates an additive motion layer (e.g. breathing)"""
        self.additive_layers[layer_name] = params

    def set_stabilization(self, roll: float, pitch: float):
        """Directly sets high-frequency stabilization offsets (additive, no smoothing)"""
        self.stab_roll = roll
        self.stab_pitch = pitch

    def clear_additive_layers(self):
        """Clears all dynamic motion layers (called at start of BT tick)"""
        self.additive_layers.clear()

    def update(self, dt: float):
        # 1. Handle Ramping (Speed)
        if self.current_speed < self.target_speed:
            self.current_speed = min(self.target_speed, self.current_speed + self.ramp_rate * dt)
        elif self.current_speed > self.target_speed:
            self.current_speed = max(self.target_speed, self.current_speed - self.ramp_rate * dt)
            
        # 2. Automated Gait Selection
        s = self.current_speed
        if s < 0.05:
            if self.current_gait != "idle": self._apply_gait("idle")
        elif s < 0.45: # Walk threshold with some hysteresis
            if self.current_gait != "walk": self._apply_gait("walk")
        else:
            if self.current_gait != "trot": self._apply_gait("trot")

        # 3. Update Body Pose Smoothing (Organic S-Curve)
        for key in self.current_body_pose:
            target = self.target_body_pose[key]
            current = self.current_body_pose[key]
            
            diff = target - current
            if abs(diff) > 0.01:
                # Calculate dynamic step based on distance (S-Curve feel)
                # Faster in the middle, slower at the ends
                # We use a simple adaptive speed: speed = base_speed * sin(progress)
                # But for dynamic targets, we can use: speed_mod = max(0.1, sin(min(progress, pi)))
                
                # Base step size
                base_step = self.smoothing_speed * dt * 25.0
                if key in ["roll", "pitch", "yaw"]: 
                    base_step = self.smoothing_speed * 15.0 * dt
                
                # Apply organic scaling: If we are close, slow down (Ease-out)
                # If we just started, we would need to know the start point.
                # Alternative: Use a fraction of the distance but capped by max speed
                dist_factor = min(1.0, abs(diff) / 10.0) # Scale down if less than 10 units away
                if key in ["roll", "pitch", "yaw"]: dist_factor = min(1.0, abs(diff) / 5.0)
                
                # Ease-in/out simulation via distance-based velocity
                actual_step = base_step * (0.2 + 0.8 * math.sin(dist_factor * math.pi / 2))
                
                if abs(diff) < actual_step:
                    self.current_body_pose[key] = target
                else:
                    self.current_body_pose[key] += math.copysign(actual_step, diff)
            else:
                self.current_body_pose[key] = target

        # 3. Update Oscillators
        t = time.time()
        
        # 4. Automatic CoM (Center of Mass) Compensation (X and Z)
        # Pitch -> X shift, Roll -> Z shift
        # We include look-at offsets for more accurate compensation
        pitch_rad = math.radians(self.current_body_pose["pitch"] + self.look_at_pitch)
        roll_rad = math.radians(self.current_body_pose["roll"] + self.look_at_yaw)
        
        # 5. Lean into turn (Organic)
        # Tilts the body slightly in the direction of the turn
        self.auto_lean = self.turn_rate * -10.0 # Max 10 deg lean
        
        # We use a tunable factor (0.8) for stability
        self.auto_com_x = math.sin(pitch_rad) * self.base_height * 0.8
        self.auto_com_z = -math.sin(roll_rad) * self.base_height * 0.8 # Counter-shift roll
        
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
        """Returns target (x,y,z) for each leg tip relative to shoulder."""
        coords = {}
        
        # 1. Gather Current Pose (Rotation Degrees -> Radians)
        # Combine intent-based smoothed pose with high-speed stabilization and refinements
        r = math.radians(self.current_body_pose["roll"] + self.stab_roll + self.auto_lean)
        p = math.radians(self.current_body_pose["pitch"] + self.stab_pitch + self.look_at_pitch)
        y = math.radians(self.current_body_pose["yaw"] + self.look_at_yaw)
        
        # DNA Phase: Blend additive layers into rotations
        for layer in self.additive_layers.values():
            r += math.radians(layer.get("roll", 0.0))
            p += math.radians(layer.get("pitch", 0.0))
            y += math.radians(layer.get("yaw", 0.0))
        
        # Base offsets + auto CoM + manual look-at
        off_x = self.current_body_pose["x"] + self.auto_com_x
        off_y = self.current_body_pose["y"]
        off_z = self.current_body_pose["z"] + self.auto_com_z
        
        # Add layer offsets (X, Y, Z)
        for layer in self.additive_layers.values():
            off_x += layer.get("x", 0.0)
            off_y += layer.get("y", 0.0)
            off_z += layer.get("z", 0.0)

        # Rotation Matrices
        # Rx (Roll) around X
        Rx = np.array([
            [1, 0, 0],
            [0, math.cos(r), -math.sin(r)],
            [0, math.sin(r), math.cos(r)]
        ])
        # Ry (Yaw) around Y
        Ry = np.array([
            [math.cos(y), 0, math.sin(y)],
            [0, 1, 0],
            [-math.sin(y), 0, math.cos(y)]
        ])
        # Rz (Pitch) around Z
        Rz = np.array([
            [math.cos(p), -math.sin(p), 0],
            [math.sin(p), math.cos(p), 0],
            [0, 0, 1]
        ])
        
        # Combined Rotation R = Ry @ Rz @ Rx (Yaw -> Pitch -> Roll)
        R = Ry @ Rz @ Rx

        for name, osc in self.oscillators.items():
            # A. Get Leg tip coordinate relative to neutral shoulder
            # lx, ly, lz is the foot position relative to the shoulder when body is flat.
            # get_coordinates returns (x, y, z) where y is distance DOWN from shoulder.
            lx, ly, lz = osc.get_coordinates(self.step_length, self.step_height, self.base_height)
            
            # B. Compensate for Turning Speed in Gait
            if self.turn_rate != 0:
                leg_speed_mod = 1.0 + (self.turn_rate if name.endswith('l') else -self.turn_rate)
                lx, ly, lz = osc.get_coordinates(self.step_length * leg_speed_mod, self.step_height, self.base_height)

            # C. Transform to Body-Relative
            # Foot in World (Absolute MM from center of neutral floor-contact body)
            # P_foot_world_y is negative because ly is distance down.
            P_foot_world = np.array([osc.base_x + lx, -ly, osc.base_z + lz])
            
            # Body displacement from neutral
            P_body = np.array([off_x, off_y, off_z])
            
            # Foot pos relative to displaced body center
            P_rel = P_foot_world - P_body
            
            # Rotate into rotated-body frame
            P_local = R.T @ P_rel
            
            # Find vector from the ROTATED shoulder joint to the foot
            # The neutral shoulder is at (osc.base_x, 0, osc.base_z) in local body frame
            P_shoulder_local = np.array([osc.base_x, 0, osc.base_z])
            P_final = P_local - P_shoulder_local
            
            # Invert Y back to "distance down" for the IK engine
            coords[name] = (P_final[0], -P_final[1], P_final[2])

        return coords

    def set_test_motion(self, motion_name: str):
        """Predefined motion patterns for servo testing"""
        m = motion_name.lower()
        if m == "all_90":
            self.set_pose("calibrate")
        elif m == "sine_wave":
            self.set_pose("normal")
            self.set_target_speed(0.1, 0.0) 
            self.step_length = 20.0
            self.step_height = 10.0
        elif m == "leg_cycle":
            self.set_pose("normal")
            self.set_target_speed(0.2, 0.0)
            self.step_length = 10.0
            self.step_height = 40.0
        elif m == "walk_cycle":
            self.set_pose("normal")
            self.set_target_speed(0.3, 0.0)
            self.step_length = 40.0
            self.step_height = 20.0
        elif m == "sit":
            self.set_pose("sit")
            self.set_target_speed(0.0, 0.0)
        elif m == "down":
            self.set_pose("down")
            self.set_target_speed(0.0, 0.0)
