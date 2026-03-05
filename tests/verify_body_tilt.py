import sys
import os
import math
import numpy as np

# Add project root to sys.path
sys.path.append(r'c:\Users\iphar\Documents\Anitgravity\Freenove_Robot\freenove_robot_new')

from movement.gait import GaitSequencer

def test_body_tilt():
    gait = GaitSequencer(base_height=100.0)
    
    print("--- Neutral Pose ---")
    coords_neutral = gait.calculate_step()
    for leg, pos in coords_neutral.items():
        print(f"{leg}: {pos}")

    print("\n--- Pitch 20 Degrees (Tilted back) ---")
    gait.current_body_pose["pitch"] = 20.0
    coords_tilted = gait.calculate_step()
    for leg, pos in coords_tilted.items():
        # Front legs (x=70) should be lower relative to shoulder (y should increase)
        # Rear legs (x=-70) should be higher relative to shoulder (y should decrease)
        # Wait, if body pitches BACK, front shoulders go UP, so feet must go DOWN relative to shoulder.
        # ly in get_coordinates is positive DOWN.
        print(f"{leg}: {pos}")

if __name__ == "__main__":
    test_body_tilt()
