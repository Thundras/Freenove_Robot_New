import logging
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

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def main():
    setup_logging()
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
            if int(time.time() * 10) % 50 == 0: # Every 5 seconds roughly
                print(f"DIAG: Main Loop Context ID: {id(intelligence.context)} Mode: {intelligence.context['system_mode']}")
            
            # A. Sensors
            imu.update()
            battery.update()
            ultrasonic.update()
            
            # B. Intelligence (Behavior Tree)
            intelligence.update()
            
            # C. Movement (Gaits & IK)
            gait.update(dt)
            target_poses = gait.calculate_step()
            
            # D. Output to Servos
            servo_ctrl.update_poses(target_poses, ik)
            
            # E. Telemetry to HA
            if int(time.time() * 10) % 50 == 0: # 0.5 Hz
                ha.publish_state("battery", battery.get_data().voltage)
                ha.publish_state("system_mode", intelligence.context["system_mode"])
            
            # --- SLEEP ---
            elapsed = time.perf_counter() - start_time
            sleep_time = max(0, dt - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested. Cleaning up...")
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
