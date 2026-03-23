import pytest
import math
from movement.ik import IKEngine


@pytest.fixture
def ik_engine():
    return IKEngine(l1=23, l2=55, l3=55)


@pytest.fixture
def ik_engine_short():
    """Leg with shorter lower segment"""
    return IKEngine(l1=20, l2=50, l3=45)


@pytest.fixture
def ik_engine_long():
    """Leg with longer segments"""
    return IKEngine(l1=30, l2=60, l3=65)


# ============================================================================
# Basic Tests
# ============================================================================


def test_fully_extended_down(ik_engine):
    """
    Fully extended leg: l1 + l2 + l3 = 23 + 55 + 55 = 133
    - Shoulder = 0° (horizontal to body)
    - Thigh = 0° (straight down)
    - Shin = 0° (aligned with thigh)
    """
    angles = ik_engine.calculate_angles(0, 133, 0)

    assert angles.shoulder == pytest.approx(0, abs=0.1)
    assert angles.thigh == pytest.approx(0, abs=0.1)
    assert angles.shin == pytest.approx(0, abs=0.1)


def test_neutral_standing(ik_engine):
    """
    Test standing position at normal height.
    The leg should be bent with positive angles.
    """
    angles = ik_engine.calculate_angles(0, 80, 0)

    # Shoulder should be 0 (horizontal to body when z=0)
    assert angles.shoulder == pytest.approx(0, abs=0.1)
    # Thigh should be positive (bending up from vertical)
    assert angles.thigh > 0
    # Shin should be positive (bent backward)
    assert angles.shin > 0


def test_sideways_right(ik_engine):
    """
    Test moving leg to the right side (positive z).
    Coxa should rotate to point outward.
    """
    angles = ik_engine.calculate_angles(0, 80, 30)

    # Coxa should be positive (rotated to right)
    assert angles.shoulder > 0


def test_sideways_left(ik_engine):
    """
    Test moving leg to the left side (negative z).
    Coxa should rotate to point outward.
    """
    angles = ik_engine.calculate_angles(0, 80, -30)

    # Coxa should be negative (rotated to left)
    assert angles.shoulder < 0


def test_forward_movement(ik_engine):
    """
    Test forward x offset affects thigh/shin angles.
    """
    angles_center = ik_engine.calculate_angles(0, 80, 0)
    angles_forward = ik_engine.calculate_angles(30, 80, 0)

    # Forward extension should change the bend
    assert angles_forward.thigh != angles_center.thigh


def test_ik_returns_leg_angles(ik_engine):
    """
    Basic sanity check that calculate_angles returns a LegAngles object.
    """
    angles = ik_engine.calculate_angles(0, 80, 0)
    assert hasattr(angles, "shoulder")
    assert hasattr(angles, "thigh")
    assert hasattr(angles, "shin")
    assert isinstance(angles.shoulder, (int, float))
    assert isinstance(angles.thigh, (int, float))
    assert isinstance(angles.shin, (int, float))


# ============================================================================
# Multi-Solution Selection Tests
# ============================================================================


def test_multi_solution_chooses_valid(ik_engine):
    """
    Test that the IK engine selects a valid solution.
    """
    angles = ik_engine.calculate_angles(0, 80, 0)
    # Should return valid angles
    assert -180 <= angles.shoulder <= 180
    assert angles.thigh >= 0  # Femur angle should be positive (bending up)
    assert angles.shin >= 0  # Tibia angle should be positive


def test_multi_solution_with_different_limits(ik_engine):
    """
    Test that limits influence solution selection.
    """
    limits = {
        "shoulder": {"limit_neg": 30, "limit_pos": 30},
        "thigh": {"limit_neg": 10, "limit_pos": 60},
        "shin": {"limit_neg": 30, "limit_pos": 120},
    }
    angles = ik_engine.calculate_angles(0, 80, 0, limits=limits)

    # Should be clamped to limits
    assert -30 <= angles.shoulder <= 30
    assert -10 <= angles.thigh <= 60


# ============================================================================
# Boundary Condition Tests
# ============================================================================


def test_minimum_reachable_height(ik_engine):
    """
    Test the minimum reachable height (closest to body).
    """
    angles = ik_engine.calculate_angles(0, 50, 0)

    # Should still return valid angles
    assert -180 <= angles.shoulder <= 180
    assert angles.thigh >= 0  # Bending up


def test_maximum_reachable_height(ik_engine):
    """
    Test the maximum reachable height (fully extended).
    """
    angles = ik_engine.calculate_angles(0, 133, 0)

    assert angles.thigh == pytest.approx(0, abs=0.5)
    assert angles.shin == pytest.approx(0, abs=0.5)


def test_beyond_maximum_height():
    """
    Test behavior when target is beyond maximum reach.
    Should clamp to maximum reachable position.
    """
    ik = IKEngine(l1=23, l2=55, l3=55)

    # Try to reach y=200 (beyond 133 max)
    angles = ik.calculate_angles(0, 200, 0)

    # Should clamp to maximum, not crash
    assert angles.thigh == pytest.approx(0, abs=2.0)
    assert angles.shin == pytest.approx(0, abs=2.0)


def test_beyond_minimum_height():
    """
    Test behavior when target is below minimum (too close).
    """
    ik = IKEngine(l1=23, l2=55, l3=55)

    # Try to reach y=10 (below minimum)
    angles = ik.calculate_angles(0, 10, 0)

    # Should handle gracefully
    assert isinstance(angles.shoulder, (int, float))


def test_sideways_limits(ik_engine):
    """
    Test behavior at extreme sideways positions.
    """
    # Extreme right
    angles_right = ik_engine.calculate_angles(0, 80, 100)
    assert angles_right.shoulder > 0

    # Extreme left
    angles_left = ik_engine.calculate_angles(0, 80, -100)
    assert angles_left.shoulder < 0


# ============================================================================
# Angle Limits and Clamping Tests
# ============================================================================


def test_angle_limits_shoulder(ik_engine):
    """
    Test that shoulder angle is clamped to limits.
    """
    limits = {
        "shoulder": {"limit_neg": 10, "limit_pos": 10},
        "thigh": {"limit_neg": 90, "limit_pos": 90},
        "shin": {"limit_neg": 90, "limit_pos": 90},
    }

    # Target that would give large shoulder angle
    angles = ik_engine.calculate_angles(0, 80, 50, limits=limits)

    # Should be clamped to +/-10
    assert -10 <= angles.shoulder <= 10


def test_angle_limits_thigh(ik_engine):
    """
    Test that thigh angle is clamped to limits.
    """
    limits = {
        "shoulder": {"limit_neg": 90, "limit_pos": 90},
        "thigh": {"limit_neg": 20, "limit_pos": 60},
        "shin": {"limit_neg": 90, "limit_pos": 90},
    }

    angles = ik_engine.calculate_angles(0, 80, 0, limits=limits)

    # Should be clamped to 20-60
    assert 20 <= angles.thigh <= 60


def test_angle_limits_shin(ik_engine):
    """
    Test that shin angle is clamped to limits.
    """
    limits = {
        "shoulder": {"limit_neg": 90, "limit_pos": 90},
        "thigh": {"limit_neg": 90, "limit_pos": 90},
        "shin": {"limit_neg": 30, "limit_pos": 100},
    }

    angles = ik_engine.calculate_angles(0, 80, 0, limits=limits)

    # Should be clamped
    assert 30 <= angles.shin <= 100


def test_no_limits_returns_valid_angles(ik_engine):
    """
    Test that no limits returns angles without clamping.
    """
    angles = ik_engine.calculate_angles(0, 80, 0, limits=None)

    # Should return mathematically valid angles
    assert -180 <= angles.shoulder <= 180
    assert angles.shin >= 0


def test_empty_limits_dict(ik_engine):
    """
    Test with empty limits dict (no clamping).
    """
    angles = ik_engine.calculate_angles(0, 80, 0, limits={})

    # Should return valid angles without error
    assert isinstance(angles.shoulder, (int, float))
    assert isinstance(angles.thigh, (int, float))


# ============================================================================
# NaN and Edge Case Tests
# ============================================================================


def test_zero_coordinates():
    """
    Test with zero x, y, z coordinates.
    """
    ik = IKEngine(l1=23, l2=55, l3=55)
    angles = ik.calculate_angles(0, 0, 0)

    # Should handle edge case gracefully
    assert isinstance(angles.shoulder, (int, float))
    assert not math.isnan(angles.shoulder)
    assert not math.isnan(angles.thigh)
    assert not math.isnan(angles.shin)


def test_negative_y():
    """
    Test with negative y (would mean above shoulder).
    """
    ik = IKEngine(l1=23, l2=55, l3=55)
    angles = ik.calculate_angles(0, -20, 0)

    # Should handle gracefully
    assert isinstance(angles.shoulder, (int, float))


def test_large_negative_x():
    """
    Test with extreme negative x (far backward).
    """
    ik = IKEngine(l1=23, l2=55, l3=55)
    angles = ik.calculate_angles(-100, 80, 0)

    assert isinstance(angles.thigh, (int, float))
    assert not math.isnan(angles.thigh)


def test_combined_extreme_values():
    """
    Test with multiple extreme values combined.
    """
    ik = IKEngine(l1=23, l2=55, l3=55)
    angles = ik.calculate_angles(50, 120, 80)

    # Should return valid angles, not NaN
    assert isinstance(angles.shoulder, (int, float))
    assert isinstance(angles.thigh, (int, float))
    assert isinstance(angles.shin, (int, float))
    assert not math.isnan(angles.shoulder)
    assert not math.isnan(angles.thigh)
    assert not math.isnan(angles.shin)


# ============================================================================
# Different Leg Configurations
# ============================================================================


def test_short_leg():
    """
    Test IK with shorter leg segments.
    """
    ik = IKEngine(l1=15, l2=40, l3=45)
    angles = ik.calculate_angles(0, 60, 0)

    assert isinstance(angles.shoulder, (int, float))
    assert angles.thigh >= 0


def test_long_leg():
    """
    Test IK with longer leg segments.
    """
    ik = IKEngine(l1=30, l2=70, l3=75)
    angles = ik.calculate_angles(0, 120, 0)

    assert isinstance(angles.shoulder, (int, float))
    assert angles.thigh >= 0


def test_equal_segment_lengths():
    """
    Test IK with all segments equal length.
    """
    ik = IKEngine(l1=30, l2=30, l3=30)
    angles = ik.calculate_angles(0, 50, 0)

    assert isinstance(angles.shoulder, (int, float))
    assert angles.thigh >= 0


def test_minimal_segment_lengths():
    """
    Test with minimal but non-zero segments.
    """
    ik = IKEngine(l1=1, l2=1, l3=1)
    angles = ik.calculate_angles(0, 2, 0)

    assert isinstance(angles.shoulder, (int, float))
    assert not math.isnan(angles.shoulder)


# ============================================================================
# Regression Tests
# ============================================================================


def test_regression_fully_extended():
    """
    Regression test: Fully extended position.
    """
    ik = IKEngine(l1=25, l2=55, l3=60)
    angles = ik.calculate_angles(0, 140, 0)

    # Should be close to vertical
    assert abs(angles.thigh) < 5
    assert angles.shin < 10


def test_regression_typical_stand():
    """
    Regression test: Typical standing height.
    """
    ik = IKEngine(l1=25, l2=55, l3=60)
    angles = ik.calculate_angles(0, 105, 0)

    # Should return valid standing angles
    assert angles.thigh > 0  # Thigh is bent up
    assert angles.shin > 0  # Shin is bent back
    assert angles.shin < 180  # Not fully bent backward


def test_regression_different_z():
    """
    Regression test: Different z values give different shoulder.
    """
    ik = IKEngine(l1=25, l2=55, l3=60)

    angles_0 = ik.calculate_angles(0, 100, 0)
    angles_25 = ik.calculate_angles(0, 100, 25)

    # Different z should give different shoulder
    assert angles_0.shoulder != angles_25.shoulder
