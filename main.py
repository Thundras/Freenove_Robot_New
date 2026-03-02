import logging
import time
import threading
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

def main():
    setup_logging()
    logger = logging.getLogger("RobotMain")
    
    logger.info("Initializing Robot Dog 2.0...")
    
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
