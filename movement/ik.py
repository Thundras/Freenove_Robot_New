import math
from dataclasses import dataclass
from typing import Tuple

@dataclass
class LegAngles:
    coxa: float
    femur: float
    tibia: float

class IKEngine:
    def __init__(self, l1: float = 23, l2: float = 55, l3: float = 55):
        """
        IK Engine for a 3-DOF robotic leg.
        :param l1: Coxa length (sidews offset)
        :param l2: Femur length
        :param l3: Tibia length
        """
        self.l1 = l1
        self.l2 = l2
        self.l3 = l3

    def calculate_angles(self, x: float, y: float, z: float) -> LegAngles:
        """
        Calculate leg angles (in degrees) for a target coordinate (x, y, z).
        x: Forward/Backward
        y: Up/Down (Height, positive is DOWN)
        z: Left/Right (Sideways)
        
        Roll-Pitch-Pitch Model:
        Coxa rotates around X (Roll) to handle Y-Z plane.
        Femur/Tibia rotate around transverse axis (Pitch) to handle X-R plane.
        """
        # 1. Coxa Angle (a) - rotation in the Y-Z plane (Roll)
        # Neutral coxa (90 deg) points straight down (y-axis)
        # z: Left/Right, y: Up/Down
        # atan2(z, y) is 0 when z=0 (straight down)
        a_rad = math.atan2(z, y) if (z != 0 or y != 0) else 0.0
        
        # 2. Distance from shoulder pivot to foot tip in the vertical Y-Z plane
        # r_yz is the projection of the leg in the Y-Z plane
        r_yz = math.sqrt(y**2 + z**2)
        # r_planar is the extension length from the femur pivot (offset l1)
        r_planar = r_yz - self.l1
        
        # 3. Solve 2D IK for Femur (b) and Tibia (c) in the r_planar-x plane
        # l23 is the distance from the femur pivot to the foot tip
        l23 = math.sqrt(r_planar**2 + x**2)
        
        # Stability check
        l23 = max(1e-6, l23)
        
        # Reachable area check
        if l23 > (self.l2 + self.l3) or l23 < abs(self.l2 - self.l3):
            if l23 > (self.l2 + self.l3):
                l23 = self.l2 + self.l3 - 1e-4
            else:
                l23 = abs(self.l2 - self.l3) + 1e-4

        # Triangle law
        cos_alpha = (self.l2**2 + l23**2 - self.l3**2) / (2 * self.l2 * l23)
        cos_alpha = max(-1.0, min(1.0, cos_alpha))
        alpha = math.acos(cos_alpha)
        
        # gamma: angle from extension axis (r_planar) to l23
        gamma = math.atan2(x, r_planar)
        
        # Femur angle (b): 0 is extending along r_planar, positive is forward.
        # Neutral (90 deg) is straight down (r_planar axis).
        b_rad = gamma + alpha
        
        # 4. Tibia Angle (c)
        cos_beta = (self.l2**2 + self.l3**2 - l23**2) / (2 * self.l2 * self.l3)
        cos_beta = max(-1.0, min(1.0, cos_beta))
        beta = math.acos(cos_beta)
        c_rad = math.pi - beta

        # Convert to degrees and apply offsets
        # Neutral (90): coxa=90 (Roll=0), femur=90 (Pitch=0), tibia=90 (Pitch=0)
        # Note: a_rad is Roll. If z=0, a_rad=0.
        # Note: b_rad is Pitch. If x=0 and r=max, alpha=0, gamma=0. 
        # But wait, at full extension (straight down), alpha=0, gamma=0.
        # We want that to be 90.
        return LegAngles(
            coxa=90.0 + math.degrees(a_rad),
            femur=90.0 + math.degrees(b_rad),
            tibia=90.0 + math.degrees(c_rad)
        )
