import pytest
import time
from movement.gait import GaitSequencer

@pytest.fixture
def gait_sequencer():
    return GaitSequencer()

def test_gait_oscillator_phases(gait_sequencer):
    """
    Check if the oscillators for different legs have the correct phase offsets for a Trot gait.
    In a Trot, opposite legs move together: (FL, RR) and (FR, RL).
    Phase offset should be 0.0 and 0.5.
    """
    gait_sequencer.set_gait("trot")
    phases = gait_sequencer.get_phases()
    
    # Check if FL and RR are in phase
    assert phases["fl"] == pytest.approx(phases["rr"], abs=0.01)
    # Check if FR and RL are in phase
    assert phases["fr"] == pytest.approx(phases["rl"], abs=0.01)
    # Check if FL and FR are out of phase by 0.5
    assert abs(phases["fl"] - phases["fr"]) == pytest.approx(0.5, abs=0.01)

def test_gait_output_coords(gait_sequencer):
    """
    Check if the sequencer generates coordinates.
    At neutral phase (0.0), the leg should be at a 'base' position.
    """
    gait_sequencer.set_gait("walk")
    coords = gait_sequencer.calculate_step(t=0.0)
    
    assert "fl" in coords
    assert len(coords["fl"]) == 3 # (x, y, z)
    
def test_ramping_acceleration(gait_sequencer):
    """
    Verify that speed increases gradually (ramping).
    """
    gait_sequencer.set_target_speed(1.0) # Target speed
    
    speed_start = gait_sequencer.current_speed
    gait_sequencer.update(dt=0.1)
    speed_mid = gait_sequencer.current_speed
    
    assert speed_start < speed_mid <= 1.0
