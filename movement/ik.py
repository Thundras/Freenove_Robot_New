import math
import logging
from dataclasses import dataclass
from typing import Tuple

logger = logging.getLogger(__name__)

@dataclass
class LegAngles:
    joint_1: float  # Schulter / Kippen (ex-Coxa)
    joint_2: float  # Oberschenkel / Beugen (ex-Femur)
    joint_3: float  # Unterschenkel / Knie (ex-Tibia)

class IKEngine:
    def __init__(self, l1: float = 25, l2: float = 55, l3: float = 60):
        """
        IK Engine for a 3-DOF robotic leg.
        :param l1: Shoulder length (sideways offset)
        :param l2: Upper leg length
        :param l3: Lower leg length
        """
        self.l1 = l1
        self.l2 = l2
        self.l3 = l3

    def calculate_angles(self, x: float, y: float, z: float, limits: dict = None) -> LegAngles:
        """
        Calculate leg angles (in degrees) for a target coordinate (x, y, z).
        x: Forward/Backward
        y: Up/Down (Height, positive is DOWN)
        z: Left/Right (Sideways)
        limits: Optional dict containing {'joint_1': {...}, 'joint_2': {...}, 'joint_3': {...}}
        """
        # 1. Coxa Angle (a) - rotation in the Y-Z plane (Roll)
        a_rad = math.atan2(z, y) if (z != 0 or y != 0) else 0.0
        
        # 2. Geometry
        r_yz = math.sqrt(y**2 + z**2)
        r_planar = r_yz - self.l1
        l23 = math.sqrt(r_planar**2 + x**2)
        
        # Stability / Reachable area check
        l23 = max(1e-6, l23)
        if l23 > (self.l2 + self.l3) or l23 < abs(self.l2 - self.l3):
            if l23 > (self.l2 + self.l3):
                l23 = self.l2 + self.l3 - 1e-4
            else:
                l23 = abs(self.l2 - self.l3) + 1e-4

        # Triangle law
        cos_alpha = (self.l2**2 + l23**2 - self.l3**2) / (2 * self.l2 * l23)
        cos_alpha = max(-1.0, min(1.0, cos_alpha))
        alpha = math.acos(cos_alpha)
        
        cos_beta = (self.l2**2 + self.l3**2 - l23**2) / (2 * self.l2 * self.l3)
        cos_beta = max(-1.0, min(1.0, cos_beta))
        beta = math.acos(cos_beta)
        
        gamma = math.atan2(x, r_planar)
        
        # --- MULTI-SOLUTION BRANCHING ---
        # Solution A: Knee-Back (Standard V-shape)
        # Solution B: Knee-Forward (Alternative Elbow-shape)
        
        def build_solution(branch_alpha, branch_beta, is_flipped=False):
            # 1. Coxa (Joint 1): 90 is perpendicular to the body.
            j1 = 90.0 + math.degrees(a_rad)
            
            # 2. Femur (Joint 2): Shifted so 90 is Horizontal.
            # 0 deg = Up, 90 deg = Horizontal, 180 deg = Vertical Down.
            # gamma + branch_alpha is absolute angle (0=Horiz, 90=Down)
            j2 = 90.0 + math.degrees(gamma + branch_alpha)
            
            # 3. Tibia (Joint 3): Internal angle at the knee.
            # 180 deg = straight leg, 90 deg = right angle bend (L-shape).
            j3 = math.degrees(branch_beta)
            
            if is_flipped:
                j3 = 180.0 - j3
                
            return LegAngles(j1, j2, j3)

        sol_a = build_solution(alpha, beta, is_flipped=False)
        sol_b = build_solution(-alpha, beta, is_flipped=True)

        def score_solution(sol):
            if not limits: return 0
            score = 0
            
            # Preference for 'Down and Forward' (Knee-Forward)
            if sol.joint_2 > 90: score += 50
            
            for part_key in ["joint_1", "joint_2", "joint_3"]:
                angle = getattr(sol, part_key)
                p_lim = limits.get(part_key)
                if p_lim:
                    l_neg = p_lim.get("limit_neg", 90)
                    l_pos = p_lim.get("limit_pos", 90)
                    delta = angle - 90.0
                    if delta < -l_neg or delta > l_pos:
                        score -= 500
                    else:
                        score -= abs(delta) * 0.1
            return score

        score_a = score_solution(sol_a)
        score_b = score_solution(sol_b)
        final_sol = sol_b if score_b >= score_a else sol_a
        
        # Final safety clamping
        if limits:
            for part_key in ["joint_1", "joint_2", "joint_3"]:
                angle = getattr(final_sol, part_key)
                p_lim = limits.get(part_key)
                if p_lim:
                    l_neg = p_lim.get("limit_neg", 70)
                    l_pos = p_lim.get("limit_pos", 70)
                    delta = angle - 90.0
                    clamped_delta = max(-l_neg, min(l_pos, delta))
                    setattr(final_sol, part_key, 90.0 + clamped_delta)
                    
                    if abs(clamped_delta - delta) > 0.01:
                        logger.debug(f"IK CLAMP for {part_key}: {angle:.1f} -> {90.0 + clamped_delta:.1f}")

        return final_sol
