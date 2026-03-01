import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class MQTTManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("mqtt", {})
        self.base_topic = self.config.get("base_topic", "freenove_dog")
        self.node_id = self.config.get("node_id", "robot_dog")
        
    def get_topic(self, category: str, name: str) -> str:
        """Generates a hierarchical topic string"""
        return f"{self.base_topic}/{self.node_id}/{category}/{name}"

    def generate_discovery_payload(self, 
                                 component_type: str, 
                                 object_id: str, 
                                 name: str, 
                                 unit: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates the JSON payload for Home Assistant MQTT Auto-Discovery.
        """
        state_topic = self.get_topic("state", object_id)
        unique_id = f"{self.node_id}_{object_id}"
        
        payload = {
            "name": name,
            "state_topic": state_topic,
            "unique_id": unique_id,
            "device": {
                "identifiers": [self.node_id],
                "name": "Freenove Robot Dog",
                "model": "Kit for Raspberry Pi",
                "manufacturer": "Freenove"
            }
        }
        
        if unit:
            payload["unit_of_measurement"] = unit
            
        return payload

    def get_discovery_topic(self, component_type: str, object_id: str) -> str:
        """The specific topic HA listens to for discovery configs"""
        return f"homeassistant/{component_type}/{self.node_id}/{object_id}/config"
