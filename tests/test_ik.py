import pytest
import math
from movement.ik import IKEngine

@pytest.fixture
def ik_engine():
    # Standard dimensions from original Freenove robot
    return IKEngine(l1=23, l2=55, l3=55)

def test_neutral_pose(ik_engine):
    """
    Test standing position (neutral pose).
    Original code starts with point [0, 99, 10] or similar.
    Let's check if the IK returns something reasonable.
    """
    # If the leg is straight down, x=0, y=99 (or similar sum of l1+l2+l3?), z=0
    # Actually, with l2=55 and l3=55, if they were inline, total length is 110.
    # But usually it stands with legs bent.
    
    # Try x=0, y=80, z=0
    angles = ik_engine.calculate_angles(0, 80, 0)
    
    # Coxa should be 90 degrees (neutral)
    assert angles.coxa == pytest.approx(90, abs=0.1)
    
    # Mathematical femur/tibia for y=80 should be around -43 and 86
    assert angles.femur < 0
    assert angles.tibia > 0

def test_fully_extended_down(ik_engine):
    """If l2=55, l3=55, fully extended is 110. Plus coxa offset."""
    # If a=90 (Coxa neutral), sin(a)=1. y = l1 + l2 + l3 = 23 + 55 + 55 = 133
    angles = ik_engine.calculate_angles(0, 133, 0)
    
    assert angles.coxa == pytest.approx(90, abs=0.1)
    assert angles.femur == pytest.approx(0, abs=0.1)
    assert angles.tibia == pytest.approx(0, abs=0.1)

def test_leg_extension(ik_engine):
    """
    If the leg is fully extended down, what are the angles?
    l2 + l3 = 110. Coxa (l1) is sideways.
    If we point it straight down (y=110, x=0, z=0 if we ignore coxa offset for a moment?)
    Wait, coxa is offset l1.
    If we want the tip to be directly under the coxa, y=ext, z=0 (local to coxa?)
    Based on angleToCoordinate, y = l3*sin(a)*cos(b+c) + ...
    """
    # Let's use a simpler test case for now: a point that is reachable.
    angles = ik_engine.calculate_angles(0, 75, 23) # z=23 is coxa length
    
    # If z=23 and y=75, and we want to reach that...
    # a = math.pi/2 - math.atan2(23, 75)
    # math.degrees(a) approx 90 - 17 = 73
    assert angles.coxa < 90

def test_unreachable_point(ik_engine):
    """Test behavior when a point is outside the workspace"""
    with pytest.raises(ValueError):
        ik_engine.calculate_angles(0, 200, 0) # Too far
