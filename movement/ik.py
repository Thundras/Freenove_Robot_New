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
        y: Up/Down (Height)
        z: Left/Right (Sideways)
        """
        # 1. Coxa Angle (a) - rotation in the Y-Z plane
        # Neutral coxa is at 90 degrees (pi/2)
        # In original code: a = math.pi/2 - math.atan2(z, y)
        a_rad = math.pi / 2 - math.atan2(z, y)
        
        # 2. Distance from coxa pivot to leg tip (Reference: docs/developer/ik_math.md)
        # We calculate the position of the coxa pivot relative to the origin after 'a' rotation.
        # This shift 'x_4' and 'x_5' compensates for the physical offset of the shoulder motor.
        x_4 = self.l1 * math.sin(a_rad)
        x_5 = self.l1 * math.cos(a_rad)
        
        # l23 is the effective length of the leg in the plane of the femur/tibia.
        # It is the 3D distance from the coxa pivot (x_5, x_4, 0) to the target (z, y, x).
        l23 = math.sqrt((z - x_5)**2 + (y - x_4)**2 + x**2)
        
        # Stability check: prevent division by zero
        l23 = max(1e-6, l23)
        
        # Reachable area check (Triangle inequality)
        # l2, l3, l23 must form a triangle
        if l23 > (self.l2 + self.l3) or l23 < abs(self.l2 - self.l3):
            raise ValueError(f"Target ({x}, {y}, {z}) is unreachable (l23={l23:.2f})")

        l2_sq = self.l2**2
        l3_sq = self.l3**2
        l23_sq = l23**2

        # 3. Femur Angle (b)
        # w = x/l23 (part of the triangle)
        # v = (l2^2 + l23^2 - l3^2) / (2 * l2 * l23)
        # b = math.asin(w) - math.acos(v)
        w = x / l23
        v = (l2_sq + l23_sq - l3_sq) / (2 * self.l2 * l23)
        
        # Stability rounding
        w = max(-1.0, min(1.0, w))
        v = max(-1.0, min(1.0, v))
        
        b_rad = math.asin(w) - math.acos(v)
        
        # 4. Tibia Angle (c)
        # c = math.pi - math.acos((l2^2 + l3^2 - l23^2) / (2 * l3 * l2))
        cos_c = (self.l2**2 + self.l3**2 - l23**2) / (2 * self.l3 * self.l2)
        cos_c = max(-1.0, min(1.0, cos_c))
        c_rad = math.pi - math.acos(cos_c)

        # Convert to degrees
        return LegAngles(
            coxa=math.degrees(a_rad),
            femur=math.degrees(b_rad),
            tibia=math.degrees(c_rad)
        )
