import os
import warnings
import logging

# 1. Silencing AI internal logs/warnings BEFORE any heavy imports
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TFLITE_LOG_SEVERITY'] = '3'
os.environ['GLOG_minloglevel'] = '3'

warnings.filterwarnings("ignore")

# Silence specific library noise
logging.getLogger('absl').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('keras').setLevel(logging.ERROR)

import sys
import time
import threading
import socket
from utils.config import ConfigManager
from sal.factory import SalFactory
from movement.gait import GaitSequencer
from movement.ik import IKEngine
from brain.intelligence import IntelligenceController
from api.ha_connectivity import HAConnectivity
from api.web_server import WebServer

# Ultimate root logging setup
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root_logger.handlers = []
root_logger.addHandler(ch)
    
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def main():
    logger = logging.getLogger("RobotMain")
    
    logger.info("Initializing Robot Dog 2.0...")
    
    # 0. Port Safety Check
    if is_port_in_use(5000):
        logger.critical("!!! PORT 5000 IS ALREADY IN USE !!!")
        
        # Visual Alarm on hardware
        try:
            led = SalFactory.get_led(config)
            led.set_pattern("blink", [255, 0, 0]) # Flash Red
            time.sleep(2)
        except: pass
        
        logger.critical("Possible 'ghost' process detected. Please run:")
        logger.critical("  Stop-Process -Name python -Force")
        logger.critical("in PowerShell before starting.")
        return # Exit early
    
    config = ConfigManager()
    
    # 1. Hardware Initialization
    servo_ctrl = SalFactory.get_servo_controller(config)
    imu = SalFactory.get_imu(config)
    battery = SalFactory.get_battery(config)
    ultrasonic = SalFactory.get_ultrasonic(config)
    buzzer = SalFactory.get_buzzer(config)
    led = SalFactory.get_led(config)
    
    # 2. Engine Initialization
    gait = GaitSequencer(base_height=90.0)
    ik = IKEngine()
    
    sensors = {"ultrasonic": ultrasonic, "imu": imu, "battery": battery, "gait": gait, "buzzer": buzzer, "led": led}
    intelligence = IntelligenceController(config, sensors=sensors, gait=gait, servo_ctrl=servo_ctrl)
    
    # 3. API & Connectivity
    ha = HAConnectivity(config, movement=gait, intelligence=intelligence)
    web = WebServer(config, movement_engine=gait, intelligence=intelligence)
    
    # Start background components
    ha.connect()
    ha.setup_discovery()
    intelligence.start()
    
    # Run Web Server in a separate thread
    web_thread = threading.Thread(target=web.run, daemon=True)
    web_thread.start()
    
    hz = config.get("system.control_loop_hz", 100)
    dt = 1.0 / hz
    
    logger.info(f"Robot ready. Control Loop running at {hz}Hz.")
    
    try:
        while True:
            start_time = time.perf_counter()
            
            # --- UPDATE CYCLE ---
            
            # A. Sensors
            imu.update()
            battery.update()
            ultrasonic.update()
            buzzer.update() # Sync mock state
            
            # B. Intelligence (Behavior Tree)
            intelligence.update()
            
            # C. Movement (Gaits & IK)
            gait.update(dt)
            target_poses = gait.calculate_step()
            
            # D. Output to Servos
            servo_ctrl.update_poses(target_poses, ik)
            
            # E. Telemetry to HA
            if int(time.time() * 10) % 10 == 0: # 1 Hz
                ha.publish_state("battery", battery.get_data().voltage)
                ha.publish_state("system_mode", intelligence.context["system_mode"])
            
            if int(time.time() * 10) % 20 == 0: # 0.5 Hz
                if intelligence and hasattr(intelligence, "mapping"):
                    m = intelligence.mapping
                    # Convert tuple keys to strings for MQTT/JSON
                    serializable_grid = {f"{k[0]},{k[1]}": v for k, v in m.grid.items()}
                    map_data = {
                        "robot_pos": m.robot_pos,
                        "robot_yaw": m.robot_yaw,
                        "grid": serializable_grid,
                        "landmarks": m.landmarks
                    }
                    ha.publish_state("env_map", map_data)
            
            # --- SLEEP ---
            elapsed = time.perf_counter() - start_time
            sleep_time = max(0, dt - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
    except Exception as e:
        logger.error(f"FATAL ERROR in main loop: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up components...")
        try:
            intelligence.stop()
        except Exception as e:
            logger.error(f"Error stopping intelligence: {e}")
            
        try:
            ha.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting HA: {e}")
            
        try:
            servo_ctrl.release_all()
        except Exception as e:
            logger.error(f"Error releasing servos: {e}")
        
        logger.info("Robot shutdown complete.")

if __name__ == "__main__":
    main()
