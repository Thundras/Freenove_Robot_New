import argparse
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import ConfigManager
from sal.factory import SalFactory

def main():
    parser = argparse.ArgumentParser(description="Servo Calibration Tool CLI")
    parser.add_argument("--channel", type=int, help="Servo channel (0-15)")
    parser.add_argument("--angle", type=int, default=90, help="Angle to set (0-180)")
    parser.add_argument("--release", action="store_true", help="Release all servos")
    
    args = parser.parse_args()
    
    config = ConfigManager()
    # Forces real mode if possible for calibration
    config._config["system"]["simulation_mode"] = False
    
    try:
        servo_ctrl = SalFactory.get_servo_controller(config)
    except Exception as e:
        print(f"Error initializing hardware: {e}")
        print("Falling back to Mock mode for dry run.")
        config._config["system"]["simulation_mode"] = True
        servo_ctrl = SalFactory.get_servo_controller(config)

    if args.release:
        servo_ctrl.release_all()
        print("All servos released.")
        return

    if args.channel is not None:
        print(f"Setting channel {args.channel} to {args.angle} degrees...")
        servo_ctrl.set_angle(args.channel, args.angle)
        print("Move complete. Check mechanical alignment.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
