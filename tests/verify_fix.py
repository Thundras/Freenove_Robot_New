import logging
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath('.'))

from movement.gait import GaitSequencer
from brain.behaviors import Idle
from api.web_server import WebServer

def test_speed_reset():
    print("Testing Speed Reset on Mode/Pose Change...")
    gait = GaitSequencer()
    gait.set_target_speed(0.5)
    gait.update(0.1)
    print(f"Initial Speed: {gait.current_speed:.2f}")

    # Simulate API call for pose change
    gait.set_pose("sit")
    gait.set_target_speed(0.0, 0.0)
    gait.update(0.1)
    print(f"Speed after Pose Change (Sit): {gait.current_speed:.2f}")
    assert gait.current_speed < 0.5 

    gait.set_target_speed(0.5)
    gait.update(0.1)
    print(f"Speed ramped back up: {gait.current_speed:.2f}")

    # Simulate API call for mode change
    gait.set_target_speed(0.0, 0.0)
    gait.update(0.1)
    print(f"Speed after Mode Change: {gait.current_speed:.2f}")
    assert gait.current_speed < 0.5

def test_idle_behavior():
    print("\nTesting Idle Behavior...")
    gait = GaitSequencer()
    gait.set_target_speed(0.5)
    gait.update(0.1)
    print(f"Moving Speed: {gait.current_speed:.2f}")
    
    idle = Idle("Idle", gait)
    idle.run()
    gait.update(0.1)
    print(f"Speed after Idle run: {gait.current_speed:.2f}")
    assert gait.target_speed == 0.0

if __name__ == "__main__":
    try:
        test_speed_reset()
        test_idle_behavior()
        print("\nVerification Successful!")
    except Exception as e:
        print(f"\nVerification Failed: {e}")
        sys.exit(1)
