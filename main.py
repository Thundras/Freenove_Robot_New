import os
import warnings
import logging

# 1. Silencing AI internal logs/warnings BEFORE any heavy imports
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TFLITE_LOG_SEVERITY"] = "3"
os.environ["GLOG_minloglevel"] = "3"

warnings.filterwarnings("ignore")

# Silence specific library noise
logging.getLogger("absl").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("keras").setLevel(logging.ERROR)

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
from utils.fail_safe import FailSafeManager, FailSafeState

# Ultimate root logging setup
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
root_logger.handlers = []
root_logger.addHandler(ch)


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def main():
    logger = logging.getLogger("RobotMain")

    logger.info("Initializing Robot Dog 2.0...")

    # 0. Port Safety Check
    config = ConfigManager()

    if is_port_in_use(5000):
        logger.critical("!!! PORT 5000 IS ALREADY IN USE !!!")

        # Visual Alarm on hardware
        try:
            led = SalFactory.get_led(config)
            if hasattr(led, "set_pattern"):
                led.set_pattern("blink", [255, 0, 0])  # Flash Red
            time.sleep(2)
        except:
            pass

        logger.critical("Possible 'ghost' process detected. Please run:")
        logger.critical("  Stop-Process -Name python -Force")
        logger.critical("in PowerShell before starting.")
        return  # Exit early

    # 1. Hardware Initialization
    servo_ctrl = SalFactory.get_servo_controller(config)
    imu = SalFactory.get_imu(config)
    battery = SalFactory.get_battery(config)
    ultrasonic = SalFactory.get_ultrasonic(config)
    buzzer = SalFactory.get_buzzer(config)
    led = SalFactory.get_led(config)

    # 2. Engine Initialization
    default_height = config.get("system.base_height", 105.0)
    gait = GaitSequencer(base_height=default_height)
    ik = IKEngine()

    sensors = {
        "ultrasonic": ultrasonic,
        "imu": imu,
        "battery": battery,
        "gait": gait,
        "buzzer": buzzer,
        "led": led,
    }
    intelligence = IntelligenceController(
        config, sensors=sensors, gait=gait, servo_ctrl=servo_ctrl
    )

    # 3. API & Connectivity
    ha = HAConnectivity(config, movement=gait, intelligence=intelligence)
    web = WebServer(
        config, movement_engine=gait, intelligence=intelligence, servo_ctrl=servo_ctrl
    )

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

    last_ha_time = 0
    last_map_time = 0
    last_battery_warning = 0

    fail_safe = FailSafeManager(config)

    try:
        while True:
            start_time = time.perf_counter()
            now_ts = time.time()

            # --- 0. FAIL-SAFE CHECK ---
            fail_safe.check_all_sensors()
            speed_mult = fail_safe.get_speed_multiplier()
            if not fail_safe.is_safe_for_movement():
                gait.set_target_speed(0.0, 0.0)
                if fail_safe.current_state == FailSafeState.EMERGENCY_STOP:
                    gait.set_pose("sit")
                    break

            # --- 1. MOVEMENT (PRIORITY) ---
            gait.update(dt)
            target_poses = gait.calculate_step()
            if speed_mult < 1.0:
                target_poses = {
                    k: (x * speed_mult, y * speed_mult, z)
                    for k, (x, y, z) in target_poses.items()
                }
            try:
                servo_ctrl.update_poses(target_poses, ik)
            except Exception as e:
                logger.error(f"Servo update failed: {e}")
                fail_safe.trigger_failsafe("servo", FailSafeState.SERVO_ERROR)
                servo_ctrl.release_all()

            # --- 2. SENSORS ---
            try:
                imu.update()
                fail_safe.update_sensor_heartbeat("imu")
            except Exception as e:
                logger.error(f"IMU update failed: {e}")
            try:
                battery.update()
            except Exception as e:
                logger.error(f"Battery update failed: {e}")
            try:
                ultrasonic.update()
                fail_safe.update_sensor_heartbeat("ultrasonic")
            except Exception as e:
                logger.error(f"Ultrasonic update failed: {e}")
            if hasattr(buzzer, "update"):
                buzzer.update()

            # --- 3. INTELLIGENCE ---
            intelligence.update()

            # --- 4. TELEMETRY (THROTTLED) ---
            # HA Telemetry (1 Hz)
            if now_ts - last_ha_time >= 1.0:
                battery_data = battery.get_data()
                if battery_data and hasattr(battery_data, "voltage"):
                    ha.publish_state("battery", battery_data.voltage)
                ha.publish_state("system_mode", intelligence.context["system_mode"])
                last_ha_time = now_ts

            # --- 4.5 BATTERY PROTECTION ---
            battery_data = battery.get_data()
            if battery_data and hasattr(battery_data, "is_low"):
                if battery_data.is_low:
                    warning_interval = config.get("battery.low_warning_interval", 30)
                    if now_ts - last_battery_warning >= warning_interval:
                        logger.warning(
                            f"LOW BATTERY: {battery_data.voltage:.1f}V "
                            f"({battery_data.percentage}%)"
                        )
                        ha.publish_state("battery_warning", True)
                        last_battery_warning = now_ts

                        if hasattr(buzzer, "beep"):
                            buzzer.beep(0.2)

                if hasattr(battery, "is_critical") and battery.is_critical():
                    logger.critical("CRITICAL BATTERY: Initiating shutdown sequence!")
                    gait.set_target_speed(0.0, 0.0)
                    gait.set_pose("sit")
                    ha.publish_state("battery_critical", True)
                    break

            # Environmental Map (High bandwidth -> Background thread)
            # Throttle to 2s based on user feedback (movement priority)
            if now_ts - last_map_time >= 2.0:
                if intelligence and hasattr(intelligence, "mapping"):
                    m = intelligence.mapping
                    serializable_grid = {f"{k[0]},{k[1]}": v for k, v in m.grid.items()}
                    map_data = {
                        "robot_pos": m.robot_pos,
                        "robot_yaw": m.robot_yaw,
                        "grid": serializable_grid,
                        "landmarks": m.landmarks,
                    }
                    ha.publish_state("env_map", map_data, use_thread=True)
                last_map_time = now_ts

            # --- PERFORMANCE MONITORING ---
            elapsed = time.perf_counter() - start_time
            if int(now_ts) % 5 == 0:
                if not hasattr(main, "_last_perf_log") or main._last_perf_log != int(
                    now_ts
                ):
                    logger.info(
                        f"[PERF] Loop frequency: {1.0 / max(0.0001, elapsed):.1f} Hz | Work time: {elapsed * 1000:.2f} ms"
                    )
                    main._last_perf_log = int(now_ts)

            # Auto-Reload Config
            if int(now_ts) % 2 == 0:
                if not hasattr(
                    main, "_last_reload_check"
                ) or main._last_reload_check != int(now_ts):
                    config.reload_if_changed()
                    main._last_reload_check = int(now_ts)

            sleep_time = max(0, dt - (time.perf_counter() - start_time))
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
