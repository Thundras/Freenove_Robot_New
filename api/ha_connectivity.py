import json
import logging
import time
from typing import Any, Dict, List, Optional
import paho.mqtt.client as mqtt
from .mqtt_manager import MQTTManager
from utils.config import ConfigManager

logger = logging.getLogger(__name__)
class HAConnectivity:
    def __init__(self, config: ConfigManager, movement=None, intelligence=None):
        self.config = config
        self.movement = movement
        self.intelligence = intelligence
        self.mqtt_mgr = MQTTManager(config._config)
        self.client = mqtt.Client()
        
        self.broker = config.get("mqtt.broker", "localhost")
        self.port = config.get("mqtt.port", 1883)
        self.username = config.get("mqtt.username")
        self.password = config.get("mqtt.password")

    def connect(self) -> bool:
        """Connect to the MQTT broker"""
        try:
            if self.username:
                self.client.username_pw_set(self.username, self.password)
            
            self.client.on_message = self.on_message
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            # Subscribe to command topics
            self.client.subscribe(self.mqtt_mgr.get_topic("cmd", "#"))
            
            logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            return False

    def setup_discovery(self):
        """Register sensors and controls in Home Assistant"""
        devices = [
            ("sensor", "battery", "Battery Voltage", "V"),
            ("sensor", "imu_roll", "IMU Roll", "°"),
            ("sensor", "imu_pitch", "IMU Pitch", "°"),
            ("select", "gait", "Gait Mode", None),
            ("select", "system_mode", "System Mode", None),
            ("camera", "vision", "Robot Perspective", None),
            ("sensor", "env_map", "Environmental Map", None)
        ]
        
        for dtype, oid, name, unit in devices:
            topic = self.mqtt_mgr.get_discovery_topic(dtype, oid)
            payload = self.mqtt_mgr.generate_discovery_payload(dtype, oid, name, unit)
            
            # Special case for Select (Gaits/Modes)
            if dtype == "select":
                if oid == "gait":
                    payload["options"] = ["trot", "walk"]
                elif oid == "system_mode":
                    payload["options"] = ["autonomous", "follow", "sit", "down", "manual", "alarm"]
                
                payload["command_topic"] = self.mqtt_mgr.get_topic("cmd", oid)
            
            # Special case for Camera
            if dtype == "camera":
                host = self.config.get("system.web_host", "localhost")
                port = self.config.get("system.web_port", 5000)
                payload["topic"] = self.mqtt_mgr.get_topic("state", oid)
                payload["mjpeg_url"] = f"http://{host}:{port}/api/camera_stream"

            # Special case for Map Sensor
            if oid == "env_map":
                # We use JSON attributes to store the complex map structure
                payload["json_attributes_topic"] = self.mqtt_mgr.get_topic("state", oid)
                payload["value_template"] = "{{ value_json.robot_pos | default('Unknown') }}"

            self.client.publish(topic, json.dumps(payload), retain=True)
            logger.info(f"Published discovery for {name}")

    def publish_state(self, object_id: str, value: Any):
        """Update a state in HA. Handles strings, numbers, and dicts (JSON)"""
        topic = self.mqtt_mgr.get_topic("state", object_id)
        if isinstance(value, (dict, list)):
            payload = json.dumps(value)
        else:
            payload = str(value)
        self.client.publish(topic, payload)

    def on_message(self, client, userdata, msg):
        """Handle incoming command messages from Home Assistant"""
        payload = msg.payload.decode()
        logger.info(f"MQTT Command received: {msg.topic} -> {payload}")
        
        topic_gait = self.mqtt_mgr.get_topic("cmd", "gait")
        topic_mode = self.mqtt_mgr.get_topic("cmd", "system_mode")
        
        if msg.topic == topic_gait:
            if self.movement:
                self.movement.set_gait(payload)
        elif msg.topic == topic_mode:
            if self.intelligence:
                self.intelligence.context["system_mode"] = payload

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
