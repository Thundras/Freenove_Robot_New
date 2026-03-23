import math
import logging
from dataclasses import dataclass
from typing import Tuple

logger = logging.getLogger(__name__)


@dataclass
class LegAngles:
    shoulder: float  # Roll rotation. 0° = horizontal to body, positive = right
    thigh: float  # Upper leg pitch. 0° = straight down, positive = up
    shin: float  # Lower leg pitch. 0° = straight (aligned with thigh), positive = bent back


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

    def calculate_angles(
        self, x: float, y: float, z: float, limits: dict = None
    ) -> LegAngles:
        """
        Calculate leg angles (in degrees) for a target coordinate (x, y, z).
        x: Forward/Backward
        y: Up/Down (Height, positive is DOWN)
        z: Left/Right (Sideways)
        limits: Optional dict containing {'shoulder': {...}, 'thigh': {...}, 'shin': {...}}
        Returns LegAngles with: shoulder (Roll), thigh (Pitch), shin (Pitch)
        """
        # 1. Shoulder Angle - Roll rotation in the Y-Z plane
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
            # 1. Shoulder: Roll rotation. 0° = horizontal to body
            s = math.degrees(a_rad)

            # 2. Thigh: Upper leg pitch from straight down
            # 0° = straight down, positive = bending up
            t = math.degrees(gamma - branch_alpha)

            # 3. Shin: Lower leg pitch. 0° = straight (aligned with thigh)
            sh = abs(180.0 - math.degrees(branch_beta))

            return LegAngles(s, t, sh)

        sol_a = build_solution(alpha, beta, is_flipped=False)
        sol_b = build_solution(-alpha, beta, is_flipped=True)

        sol_a = build_solution(alpha, beta, is_flipped=False)
        sol_b = build_solution(-alpha, beta, is_flipped=True)

        def score_solution(sol):
            if not limits:
                return 0
            score = 0

            # Prefer solutions that keep the leg closer to vertical (thigh near 0)
            score -= abs(sol.thigh) * 0.5

            for part_key in ["shoulder", "thigh", "shin"]:
                angle = getattr(sol, part_key)
                p_lim = limits.get(part_key)
                if p_lim:
                    l_neg = p_lim.get("limit_neg", 90)
                    l_pos = p_lim.get("limit_pos", 90)
                    if angle < -l_neg or angle > l_pos:
                        score -= 500
                    else:
                        score -= abs(angle) * 0.1
            return score

        score_a = score_solution(sol_a)
        score_b = score_solution(sol_b)
        final_sol = sol_b if score_b >= score_a else sol_a

        # Final safety clamping
        if limits:
            for part_key in ["shoulder", "thigh", "shin"]:
                angle = getattr(final_sol, part_key)
                p_lim = limits.get(part_key)
                if p_lim:
                    l_neg = p_lim.get("limit_neg", 90)
                    l_pos = p_lim.get("limit_pos", 90)
                    clamped_angle = max(-l_neg, min(l_pos, angle))
                    setattr(final_sol, part_key, clamped_angle)

                    if abs(clamped_angle - angle) > 0.01:
                        logger.debug(
                            f"IK CLAMP for {part_key}: {angle:.1f} -> {clamped_angle:.1f}"
                        )

        return final_sol
