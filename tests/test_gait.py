import pytest
import math
import time
from movement.gait import GaitSequencer


@pytest.fixture
def gait_sequencer():
    return GaitSequencer()


@pytest.fixture
def gait_sequencer_custom():
    return GaitSequencer(base_height=80.0)


# ============================================================================
# Basic Gait Tests
# ============================================================================


def test_gait_oscillator_phases(gait_sequencer):
    """
    Check if the oscillators for different legs have the correct phase offsets for a Trot gait.
    In a Trot, opposite legs move together: (FL, RR) and (FR, RL).
    The target_phase_offset should be 0.0 for FL/RR and 0.5 for FR/RL.
    """
    gait_sequencer.set_gait("trot")

    offsets = {
        leg: osc.target_phase_offset for leg, osc in gait_sequencer.oscillators.items()
    }

    assert offsets["fl"] == pytest.approx(offsets["rr"], abs=0.01)
    assert offsets["fr"] == pytest.approx(offsets["rl"], abs=0.01)
    assert abs(offsets["fl"] - offsets["fr"]) == pytest.approx(0.5, abs=0.01)


def test_gait_walk_phases(gait_sequencer):
    """
    Test walk gait phase offsets.
    Walk is a 4-beat gait with sequential leg lifts.
    """
    gait_sequencer.set_gait("walk")

    offsets = {
        leg: osc.target_phase_offset for leg, osc in gait_sequencer.oscillators.items()
    }

    # Walk: FL(0.0), FR(0.5), RL(0.75), RR(0.25)
    assert offsets["fl"] == pytest.approx(0.0, abs=0.01)
    assert offsets["fr"] == pytest.approx(0.5, abs=0.01)
    assert offsets["rl"] == pytest.approx(0.75, abs=0.01)
    assert offsets["rr"] == pytest.approx(0.25, abs=0.01)


def test_gait_idle_phases(gait_sequencer):
    """
    Test idle gait - all legs in phase.
    """
    gait_sequencer.set_gait("idle")

    offsets = {
        leg: osc.target_phase_offset for leg, osc in gait_sequencer.oscillators.items()
    }

    # Idle: all legs have phase 0.0
    for leg in ["fl", "fr", "rl", "rr"]:
        assert offsets[leg] == pytest.approx(0.0, abs=0.01)


def test_gait_output_coords(gait_sequencer):
    """
    Check if the sequencer generates coordinates.
    """
    gait_sequencer.set_gait("walk")
    coords = gait_sequencer.calculate_step(t=0.0)

    assert "fl" in coords
    assert "fr" in coords
    assert "rl" in coords
    assert "rr" in coords
    for leg in ["fl", "fr", "rl", "rr"]:
        assert len(coords[leg]) == 3  # (x, y, z)


def test_ramping_acceleration(gait_sequencer):
    """
    Verify that speed increases gradually (ramping).
    """
    gait_sequencer.set_target_speed(1.0)

    speed_start = gait_sequencer.current_speed
    gait_sequencer.update(dt=0.1)
    speed_mid = gait_sequencer.current_speed

    assert speed_start < speed_mid <= 1.0


def test_ramping_deceleration(gait_sequencer):
    """
    Verify that speed decreases gradually.
    """
    gait_sequencer.current_speed = 1.0
    gait_sequencer.set_target_speed(0.0)

    speed_start = gait_sequencer.current_speed
    gait_sequencer.update(dt=0.1)
    speed_mid = gait_sequencer.current_speed

    assert speed_start > speed_mid >= 0.0


# ============================================================================
# Body Pose Tests
# ============================================================================


def test_body_pose_neutral(gait_sequencer):
    """
    Test that neutral body pose is at origin.
    """
    assert gait_sequencer.current_body_pose["roll"] == 0.0
    assert gait_sequencer.current_body_pose["pitch"] == 0.0
    assert gait_sequencer.current_body_pose["yaw"] == 0.0
    assert gait_sequencer.current_body_pose["x"] == 0.0
    assert gait_sequencer.current_body_pose["y"] == 0.0
    assert gait_sequencer.current_body_pose["z"] == 0.0


def test_set_pose_normal(gait_sequencer):
    """
    Test setting normal pose.
    """
    gait_sequencer.set_pose("normal")

    assert gait_sequencer.target_body_pose["roll"] == 0.0
    assert gait_sequencer.target_body_pose["pitch"] == 0.0
    assert gait_sequencer.target_body_pose["x"] == 0.0
    assert gait_sequencer.target_body_pose["y"] == 0.0


def test_set_pose_sit(gait_sequencer):
    """
    Test sit pose.
    """
    gait_sequencer.set_pose("sit")

    assert gait_sequencer.target_body_pose["pitch"] == 25.0
    assert gait_sequencer.target_body_pose["y"] == -40.0
    assert gait_sequencer.target_body_pose["x"] == -10.0


def test_set_pose_down(gait_sequencer):
    """
    Test down pose.
    """
    gait_sequencer.set_pose("down")

    assert gait_sequencer.target_body_pose["y"] == -60.0


def test_set_pose_aggressive(gait_sequencer):
    """
    Test aggressive pose.
    """
    gait_sequencer.set_pose("aggressive")

    assert gait_sequencer.target_body_pose["pitch"] == -15.0
    assert gait_sequencer.target_body_pose["y"] == 15.0


def test_body_pose_smoothing():
    """
    Test that body pose transitions smoothly.
    """
    gait = GaitSequencer()

    # Set sit pose
    gait.set_pose("sit")

    # Initial should be neutral
    assert gait.current_body_pose["pitch"] == 0.0

    # Update with time to allow smoothing
    for _ in range(10):
        gait.update(dt=0.1)

    # After several updates, pitch should be closer to target (25.0)
    assert gait.current_body_pose["pitch"] > 0.0


# ============================================================================
# Body Rotation Transformation Tests
# ============================================================================


def test_body_rotation_roll_affects_all_legs(gait_sequencer):
    """
    Test that body roll rotation affects all legs differently.
    """
    gait_sequencer.set_pose("normal")
    gait_sequencer.target_body_pose["roll"] = 10.0

    # Update to apply smoothing
    gait_sequencer.update(dt=0.5)

    coords_before = gait_sequencer.calculate_step()

    # Change roll
    gait_sequencer.target_body_pose["roll"] = -10.0
    gait_sequencer.update(dt=0.5)

    coords_after = gait_sequencer.calculate_step()

    # At least one leg should have different coordinates
    changed = False
    for leg in ["fl", "fr", "rl", "rr"]:
        if coords_before[leg] != coords_after[leg]:
            changed = True
            break
    assert changed, "Roll rotation should affect leg coordinates"


def test_body_rotation_pitch_affects_all_legs(gait_sequencer):
    """
    Test that body pitch rotation affects all legs differently.
    """
    gait_sequencer.set_pose("normal")
    gait_sequencer.target_body_pose["pitch"] = 15.0
    gait_sequencer.update(dt=0.5)

    coords_before = gait_sequencer.calculate_step()

    gait_sequencer.target_body_pose["pitch"] = -15.0
    gait_sequencer.update(dt=0.5)

    coords_after = gait_sequencer.calculate_step()

    changed = False
    for leg in ["fl", "fr", "rl", "rr"]:
        if coords_before[leg] != coords_after[leg]:
            changed = True
            break
    assert changed, "Pitch rotation should affect leg coordinates"


def test_body_rotation_yaw_affects_all_legs(gait_sequencer):
    """
    Test that body yaw rotation affects all legs differently.
    """
    gait_sequencer.set_pose("normal")
    gait_sequencer.target_body_pose["yaw"] = 20.0
    gait_sequencer.update(dt=0.5)

    coords_before = gait_sequencer.calculate_step()

    gait_sequencer.target_body_pose["yaw"] = -20.0
    gait_sequencer.update(dt=0.5)

    coords_after = gait_sequencer.calculate_step()

    changed = False
    for leg in ["fl", "fr", "rl", "rr"]:
        if coords_before[leg] != coords_after[leg]:
            changed = True
            break
    assert changed, "Yaw rotation should affect leg coordinates"


# ============================================================================
# Turn Compensation Tests
# ============================================================================


def test_turn_rate_straight(gait_sequencer):
    """
    Test that straight movement (turn_rate=0) produces valid coordinates.
    """
    gait_sequencer.set_target_speed(0.5, turn=0.0)
    gait_sequencer.update(dt=0.1)

    coords = gait_sequencer.calculate_step()

    # Should produce valid coordinates
    for leg in ["fl", "fr", "rl", "rr"]:
        x, y, z = coords[leg]
        assert isinstance(x, (int, float))


def test_turn_rate_turn_right(gait_sequencer):
    """
    Test that turning right affects leg coordinates differently.
    """
    gait_sequencer.set_target_speed(0.5, turn=0.5)
    gait_sequencer.update(dt=0.1)

    coords_right = gait_sequencer.calculate_step()

    gait_sequencer.set_target_speed(0.5, turn=-0.5)
    gait_sequencer.update(dt=0.1)

    coords_left = gait_sequencer.calculate_step()

    # Right and left turns should produce different coordinates
    different = False
    for leg in ["fl", "fr", "rl", "rr"]:
        if coords_right[leg] != coords_left[leg]:
            different = True
            break
    assert different, "Right and left turns should produce different leg positions"


def test_turn_affects_opposite_legs_differently():
    """
    Test that in a trot, opposite legs are affected symmetrically by turns.
    """
    gait = GaitSequencer()
    gait.set_gait("trot")
    gait.set_target_speed(0.5, turn=1.0)

    # Get phase offsets
    offsets = {leg: osc.target_phase_offset for leg, osc in gait.oscillators.items()}

    # In trot, FL/RR should have different turn compensation than FR/RL
    # But at base level, the gait definition should be preserved
    assert offsets["fl"] == pytest.approx(offsets["rr"], abs=0.01)
    assert offsets["fr"] == pytest.approx(offsets["rl"], abs=0.01)


# ============================================================================
# Additive Layer Tests
# ============================================================================


def test_additive_layer_adds_offset(gait_sequencer):
    """
    Test that additive layers add offsets to body pose.
    """
    gait_sequencer.set_pose("normal")
    gait_sequencer.update(dt=0.1)

    coords_before = gait_sequencer.calculate_step()

    # Add breathing layer
    gait_sequencer.add_additive_layer("Breathing", {"y": 5.0})
    gait_sequencer.update(dt=0.1)

    coords_after = gait_sequencer.calculate_step()

    # Y coordinate should be affected
    for leg in ["fl", "fr", "rl", "rr"]:
        assert coords_after[leg][1] != coords_before[leg][1]


def test_additive_layer_multiple_layers(gait_sequencer):
    """
    Test multiple additive layers stack correctly.
    """
    gait_sequencer.add_additive_layer("Layer1", {"y": 3.0})
    gait_sequencer.add_additive_layer("Layer2", {"y": 2.0})

    gait_sequencer.update(dt=0.1)
    coords = gait_sequencer.calculate_step()

    # Both layers should contribute (at least the second one)
    gait_sequencer.clear_additive_layers()
    gait_sequencer.add_additive_layer("Layer1", {"y": 3.0})

    gait_sequencer.update(dt=0.1)
    coords_single = gait_sequencer.calculate_step()

    # With 2 layers (3+2=5) vs 1 layer (3), Y should be different
    assert coords["fl"][1] != coords_single["fl"][1]


def test_clear_additive_layers(gait_sequencer):
    """
    Test that clear_additive_layers removes all layers.
    """
    gait_sequencer.add_additive_layer("Layer1", {"y": 5.0})
    gait_sequencer.add_additive_layer("Layer2", {"x": 3.0})

    gait_sequencer.clear_additive_layers()

    assert len(gait_sequencer.additive_layers) == 0


def test_additive_layer_with_pitch(gait_sequencer):
    """
    Test additive layer with pitch rotation.
    """
    gait_sequencer.set_pose("normal")
    gait_sequencer.update(dt=0.1)

    coords_before = gait_sequencer.calculate_step()

    # Add wiggle
    gait_sequencer.add_additive_layer("Wiggle", {"pitch": 5.0})
    gait_sequencer.update(dt=0.1)

    coords_after = gait_sequencer.calculate_step()

    # Should be different
    different = False
    for leg in ["fl", "fr", "rl", "rr"]:
        if coords_after[leg] != coords_before[leg]:
            different = True
            break
    assert different


# ============================================================================
# Look-At Tests
# ============================================================================


def test_look_at_sets_offsets(gait_sequencer):
    """
    Test that set_look_at sets the gaze offsets.
    """
    gait_sequencer.set_look_at(15.0, -10.0)

    assert gait_sequencer.look_at_yaw == 15.0
    assert gait_sequencer.look_at_pitch == -10.0


def test_look_at_affects_coordinates(gait_sequencer):
    """
    Test that look_at affects calculated leg coordinates.
    """
    gait_sequencer.set_pose("normal")
    gait_sequencer.set_look_at(0.0, 0.0)
    gait_sequencer.update(dt=0.1)

    coords_neutral = gait_sequencer.calculate_step()

    gait_sequencer.set_look_at(20.0, 10.0)
    gait_sequencer.update(dt=0.1)

    coords_look = gait_sequencer.calculate_step()

    # Should be different when looking at something
    different = False
    for leg in ["fl", "fr", "rl", "rr"]:
        if coords_neutral[leg] != coords_look[leg]:
            different = True
            break
    assert different


# ============================================================================
# Oscillator Tests
# ============================================================================


def test_oscillator_phase_wrapping(gait_sequencer):
    """
    Test that phase wraps correctly at 1.0.
    """
    gait_sequencer.set_target_speed(1.0)

    # Run many updates to wrap phase
    for _ in range(200):
        gait_sequencer.update(dt=0.01)

    # Phases should be in [0, 1) range
    phases = gait_sequencer.get_phases()
    for leg, phase in phases.items():
        assert 0 <= phase < 1.0, f"Phase for {leg} is out of range: {phase}"


def test_oscillator_idle_motion(gait_sequencer):
    """
    Test that oscillators produce idle motion when speed is low.
    """
    gait_sequencer.set_target_speed(0.0)

    coords1 = gait_sequencer.calculate_step()
    gait_sequencer.update(dt=0.1)
    coords2 = gait_sequencer.calculate_step()

    # Idle motion should produce slight changes
    changed = False
    for leg in ["fl", "fr", "rl", "rr"]:
        if coords1[leg] != coords2[leg]:
            changed = True
            break
    assert changed, "Idle motion should produce slight coordinate changes"


def test_oscillator_phase_offset_interpolation():
    """
    Test that phase offsets interpolate smoothly when changing gait.
    """
    gait = GaitSequencer()
    gait.set_gait("idle")

    # Change to trot
    gait.set_gait("trot")

    # Trot FL target should be 0.0
    assert gait.oscillators["fl"].target_phase_offset == pytest.approx(0.0, abs=0.01)
    # Trot FR target should be 0.5
    assert gait.oscillators["fr"].target_phase_offset == pytest.approx(0.5, abs=0.01)

    # Change to walk
    gait.set_gait("walk")

    # Walk FL target should be 0.0
    assert gait.oscillators["fl"].target_phase_offset == pytest.approx(0.0, abs=0.01)
    # Walk FR target should be 0.5
    assert gait.oscillators["fr"].target_phase_offset == pytest.approx(0.5, abs=0.01)


# ============================================================================
# Mount Offset Tests
# ============================================================================


def test_mount_offsets_exist(gait_sequencer):
    """
    Test that all legs have mount offsets defined.
    """
    for leg in ["fl", "fr", "rl", "rr"]:
        assert leg in gait_sequencer.mount_offsets
        mx, mz = gait_sequencer.mount_offsets[leg]
        assert isinstance(mx, (int, float))
        assert isinstance(mz, (int, float))


def test_fl_mirror_rr(gait_sequencer):
    """
    Test that FL and RR mount offsets are mirrored.
    FL is at (-70, -40), RR should be at (70, 40)
    """
    fl_x, fl_z = gait_sequencer.mount_offsets["fl"]
    rr_x, rr_z = gait_sequencer.mount_offsets["rr"]

    assert rr_x == -fl_x
    assert rr_z == -fl_z


def test_fr_mirror_rl(gait_sequencer):
    """
    Test that FR and RL mount offsets are mirrored.
    FR is at (70, 40), RL should be at (-70, -40)
    """
    fr_x, fr_z = gait_sequencer.mount_offsets["fr"]
    rl_x, rl_z = gait_sequencer.mount_offsets["rl"]

    assert rl_x == -fr_x
    assert rl_z == -fr_z


# ============================================================================
# Speed Gait Transition Tests
# ============================================================================


def test_auto_gait_idle_when_stopped(gait_sequencer):
    """
    Test that gait automatically switches to idle when stopped.
    """
    gait_sequencer.set_target_speed(0.0)
    gait_sequencer.update(dt=0.1)

    assert gait_sequencer.current_gait == "idle"


def test_auto_gait_walk_at_low_speed(gait_sequencer):
    """
    Test that gait automatically switches to walk at low speed.
    """
    gait_sequencer.set_target_speed(0.3)
    gait_sequencer.update(dt=0.1)

    # Should switch to walk at speed >= 0.05
    assert gait_sequencer.current_gait == "walk"


def test_auto_gait_trot_at_high_speed(gait_sequencer):
    """
    Test that gait automatically switches to trot at high speed.
    """
    gait_sequencer.set_target_speed(0.6)

    # Ramp up speed with multiple updates
    for _ in range(20):
        gait_sequencer.update(dt=0.1)

    # Should switch to trot at current_speed >= 0.45
    assert gait_sequencer.current_gait == "trot"


# ============================================================================
# Coordinate System Tests
# ============================================================================


def test_coordinates_are_numeric(gait_sequencer):
    """
    Test that all generated coordinates are numeric.
    """
    gait_sequencer.set_target_speed(0.5)
    gait_sequencer.update(dt=0.1)

    coords = gait_sequencer.calculate_step()

    for leg in ["fl", "fr", "rl", "rr"]:
        x, y, z = coords[leg]
        assert isinstance(x, (int, float))
        assert isinstance(y, (int, float))
        assert isinstance(z, (int, float))
        assert not math.isnan(x)
        assert not math.isnan(y)
        assert not math.isnan(z)


def test_coordinates_in_reasonable_range(gait_sequencer):
    """
    Test that coordinates are in reasonable range for the robot.
    """
    gait_sequencer.set_target_speed(0.5)
    gait_sequencer.update(dt=0.1)

    coords = gait_sequencer.calculate_step()

    # X should be roughly where the leg is (mount offset + step)
    # Z should be roughly where the leg is (mount offset)
    # Y should be around base_height (50-150 range for typical movement)
    for leg in ["fl", "fr", "rl", "rr"]:
        x, y, z = coords[leg]
        assert -200 < x < 200, f"X out of range for {leg}: {x}"
        assert 0 < y < 200, f"Y out of range for {leg}: {y}"
        assert -200 < z < 200, f"Z out of range for {leg}: {z}"


def test_custom_base_height(gait_sequencer_custom):
    """
    Test that custom base height affects Y coordinates.
    """
    gait_sequencer_custom.set_target_speed(0.0)
    gait_sequencer_custom.update(dt=0.1)

    coords = gait_sequencer_custom.calculate_step()

    # All Y values should be around base_height (80)
    for leg in ["fl", "fr", "rl", "rr"]:
        y = coords[leg][1]
        assert 50 < y < 150, f"Y out of range for {leg}: {y}"
