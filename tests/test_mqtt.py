import pytest
from api.mqtt_manager import MQTTManager
from utils.config import ConfigManager

@pytest.fixture
def mqtt_config():
    return {
        "mqtt": {
            "broker": "localhost",
            "port": 1883,
            "base_topic": "freenove_dog",
            "node_id": "robot_dog_01"
        }
    }

def test_mqtt_topic_generation(mqtt_config):
    """Verify that topics are correctly generated based on config"""
    manager = MQTTManager(mqtt_config)
    
    # Sensor Topic
    sensor_topic = manager.get_topic("sensor", "battery")
    assert sensor_topic == "freenove_dog/robot_dog_01/sensor/battery"
    
    # Command Topic
    cmd_topic = manager.get_topic("cmd", "move")
    assert cmd_topic == "freenove_dog/robot_dog_01/cmd/move"

def test_ha_discovery_payload(mqtt_config):
    """Verify the structure of the Home Assistant discovery payload"""
    manager = MQTTManager(mqtt_config)
    payload = manager.generate_discovery_payload("sensor", "battery", "Battery", "V")
    
    assert "state_topic" in payload
    assert "unique_id" in payload
    assert payload["unit_of_measurement"] == "V"
    assert "robot_dog_01" in payload["unique_id"]
