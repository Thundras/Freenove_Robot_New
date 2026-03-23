import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
import json
from api.mqtt_manager import MQTTManager
from api.ha_connectivity import HAConnectivity


@pytest.fixture
def mqtt_config():
    return {
        "mqtt": {
            "broker": "localhost",
            "port": 1883,
            "base_topic": "freenove_dog",
            "node_id": "robot_dog_01",
        }
    }


class TestMQTTManager:
    def test_topic_generation_sensor(self, mqtt_config):
        """Verify sensor topics are correctly generated"""
        manager = MQTTManager(mqtt_config)

        topic = manager.get_topic("sensor", "battery")
        assert topic == "freenove_dog/robot_dog_01/sensor/battery"

    def test_topic_generation_command(self, mqtt_config):
        """Verify command topics are correctly generated"""
        manager = MQTTManager(mqtt_config)

        topic = manager.get_topic("cmd", "move")
        assert topic == "freenove_dog/robot_dog_01/cmd/move"

    def test_topic_generation_state(self, mqtt_config):
        """Verify state topics are correctly generated"""
        manager = MQTTManager(mqtt_config)

        topic = manager.get_topic("state", "battery")
        assert topic == "freenove_dog/robot_dog_01/state/battery"

    def test_topic_with_special_characters(self, mqtt_config):
        """Verify topics handle special characters"""
        manager = MQTTManager(mqtt_config)

        topic = manager.get_topic("sensor", "imu_roll")
        assert "imu_roll" in topic
        assert topic.startswith("freenove_dog/robot_dog_01/sensor/")

    def test_ha_discovery_payload_sensor(self, mqtt_config):
        """Verify Home Assistant sensor discovery payload"""
        manager = MQTTManager(mqtt_config)
        payload = manager.generate_discovery_payload(
            "sensor", "battery", "Battery", "V"
        )

        assert "state_topic" in payload
        assert "unique_id" in payload
        assert payload["unique_id"] == "robot_dog_01_battery"
        assert payload["unit_of_measurement"] == "V"
        assert payload["state_topic"] == "freenove_dog/robot_dog_01/state/battery"

    def test_ha_discovery_payload_select(self, mqtt_config):
        """Verify Home Assistant select discovery payload"""
        manager = MQTTManager(mqtt_config)
        payload = manager.generate_discovery_payload(
            "select", "gait", "Gait Mode", None
        )

        assert payload["name"] == "Gait Mode"
        assert payload["unique_id"] == "robot_dog_01_gait"
        assert "device" in payload
        assert "Freenove Robot Dog" in payload["device"]["name"]

    def test_ha_discovery_payload_without_unit(self, mqtt_config):
        """Verify payload works without unit of measurement"""
        manager = MQTTManager(mqtt_config)
        payload = manager.generate_discovery_payload(
            "sensor", "temp", "Temperature", None
        )

        assert "unit_of_measurement" not in payload

    def test_discovery_topic_generation(self, mqtt_config):
        """Verify Home Assistant discovery topics"""
        manager = MQTTManager(mqtt_config)

        topic = manager.get_discovery_topic("sensor", "battery")
        assert topic == "homeassistant/sensor/robot_dog_01/battery/config"

    def test_default_values(self):
        """Verify default values when config is minimal"""
        config = {}
        manager = MQTTManager(config)

        assert manager.base_topic == "freenove_dog"
        assert manager.node_id == "robot_dog"

    def test_custom_config_values(self, mqtt_config):
        """Verify custom config values are used"""
        manager = MQTTManager(mqtt_config)

        assert manager.base_topic == "freenove_dog"
        assert manager.node_id == "robot_dog_01"


class TestHAConnectivity:
    @pytest.fixture
    def mock_config(self, mqtt_config):
        """Create a mock config manager"""
        mock_cfg = Mock()
        mock_cfg._config = mqtt_config

        def get_value(key, default=None):
            keys = key.split(".")
            val = mqtt_config
            try:
                for k in keys:
                    val = val[k]
                return val
            except (KeyError, TypeError):
                return default

        mock_cfg.get = get_value
        return mock_cfg

    @patch("api.ha_connectivity.mqtt.Client")
    def test_connect_success(self, mock_client_class, mock_config):
        """Test successful connection to MQTT broker"""
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        ha = HAConnectivity(mock_config)
        result = ha.connect()

        assert result is True
        mock_client_instance.connect.assert_called_once_with("localhost", 1883, 60)
        mock_client_instance.loop_start.assert_called_once()

    @patch("api.ha_connectivity.mqtt.Client")
    def test_connect_with_credentials(self, mock_client_class, mock_config):
        """Test connection with username/password"""
        mock_config._config["mqtt"]["username"] = "test_user"
        mock_config._config["mqtt"]["password"] = "test_pass"

        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        ha = HAConnectivity(mock_config)
        ha.connect()

        mock_client_instance.username_pw_set.assert_called_once_with(
            "test_user", "test_pass"
        )

    @patch("api.ha_connectivity.mqtt.Client")
    def test_connect_failure(self, mock_client_class, mock_config):
        """Test connection failure handling"""
        mock_client_instance = Mock()
        mock_client_instance.connect.side_effect = Exception("Connection refused")
        mock_client_class.return_value = mock_client_instance

        ha = HAConnectivity(mock_config)
        result = ha.connect()

        assert result is False

    @patch("api.ha_connectivity.mqtt.Client")
    def test_subscribe_to_commands(self, mock_client_class, mock_config):
        """Test subscription to command topics"""
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        ha = HAConnectivity(mock_config)
        ha.connect()

        mock_client_instance.subscribe.assert_called()
        call_args = mock_client_instance.subscribe.call_args
        subscribed_topic = call_args[0][0]
        assert "cmd" in subscribed_topic
        assert "#" in subscribed_topic

    @patch("api.ha_connectivity.mqtt")
    def test_publish_state_number(self, mock_mqtt, mock_config):
        """Test publishing numeric state"""
        ha = HAConnectivity(mock_config)
        mock_client_instance = Mock()
        mock_client_instance.is_connected.return_value = True
        mock_mqtt.Client.return_value = mock_client_instance

        ha.client = mock_client_instance
        ha.publish_state("battery", 12.5)

        mock_client_instance.publish.assert_called()
        topic, payload = mock_client_instance.publish.call_args[0]
        assert "state/battery" in topic
        assert payload == "12.5"

    @patch("api.ha_connectivity.mqtt")
    def test_publish_state_dict(self, mock_mqtt, mock_config):
        """Test publishing dictionary state as JSON"""
        ha = HAConnectivity(mock_config)
        mock_client_instance = Mock()
        mock_client_instance.is_connected.return_value = True
        mock_mqtt.Client.return_value = mock_client_instance

        ha.client = mock_client_instance
        state = {"x": 10, "y": 20, "z": 5}
        ha.publish_state("position", state)

        mock_client_instance.publish.assert_called()
        topic, payload = mock_client_instance.publish.call_args[0]
        assert "state/position" in topic
        parsed = json.loads(payload)
        assert parsed["x"] == 10

    @patch("api.ha_connectivity.mqtt")
    def test_publish_state_disconnected(self, mock_mqtt, mock_config):
        """Test publishing when disconnected does nothing"""
        ha = HAConnectivity(mock_config)
        mock_client_instance = Mock()
        mock_client_instance.is_connected.return_value = False
        mock_mqtt.Client.return_value = mock_client_instance

        ha.client = mock_client_instance
        ha.publish_state("battery", 12.5)

        mock_client_instance.publish.assert_not_called()

    @patch("api.ha_connectivity.mqtt")
    def test_setup_discovery_sensors(self, mock_mqtt, mock_config):
        """Test Home Assistant discovery for sensors"""
        ha = HAConnectivity(mock_config)
        mock_client_instance = Mock()
        mock_mqtt.Client.return_value = mock_client_instance

        ha.client = mock_client_instance
        ha.setup_discovery()

        assert mock_client_instance.publish.call_count >= 3
        battery_call = [
            c
            for c in mock_client_instance.publish.call_args_list
            if "battery" in str(c) and "config" in str(c)
        ]
        assert len(battery_call) > 0

    @patch("api.ha_connectivity.mqtt")
    def test_setup_discovery_select_with_options(self, mock_mqtt, mock_config):
        """Test gait select has correct options"""
        ha = HAConnectivity(mock_config)
        mock_client_instance = Mock()
        mock_mqtt.Client.return_value = mock_client_instance

        ha.client = mock_client_instance
        ha.setup_discovery()

        gait_call = [
            c
            for c in mock_client_instance.publish.call_args_list
            if "gait" in str(c[0])
        ]
        assert len(gait_call) > 0
        _, payload = gait_call[0][0]
        parsed = json.loads(payload)
        assert "options" in parsed
        assert "trot" in parsed["options"]
        assert "walk" in parsed["options"]

    @patch("api.ha_connectivity.mqtt")
    def test_setup_discovery_mode_options(self, mock_mqtt, mock_config):
        """Test system_mode select has correct options"""
        ha = HAConnectivity(mock_config)
        mock_client_instance = Mock()
        mock_mqtt.Client.return_value = mock_client_instance

        ha.client = mock_client_instance
        ha.setup_discovery()

        mode_call = [
            c
            for c in mock_client_instance.publish.call_args_list
            if "system_mode" in str(c[0])
        ]
        assert len(mode_call) > 0
        _, payload = mode_call[0][0]
        parsed = json.loads(payload)
        assert "options" in parsed
        assert "autonomous" in parsed["options"]
        assert "alarm" in parsed["options"]

    @patch("api.ha_connectivity.mqtt")
    def test_on_message_gait_command(self, mock_mqtt, mock_config):
        """Test handling gait command from MQTT"""
        mock_movement = Mock()

        ha = HAConnectivity(mock_config, movement=mock_movement)

        mock_msg = Mock()
        mock_msg.topic = "freenove_dog/robot_dog_01/cmd/gait"
        mock_msg.payload = b"trot"

        ha.on_message(None, None, mock_msg)

        mock_movement.set_gait.assert_called_once_with("trot")

    @patch("api.ha_connectivity.mqtt")
    def test_on_message_mode_command(self, mock_mqtt, mock_config):
        """Test handling system_mode command from MQTT"""
        mock_intelligence = Mock()
        mock_intelligence.context = {"system_mode": "manual"}

        ha = HAConnectivity(mock_config, intelligence=mock_intelligence)

        mock_msg = Mock()
        mock_msg.topic = "freenove_dog/robot_dog_01/cmd/system_mode"
        mock_msg.payload = b"autonomous"

        ha.on_message(None, None, mock_msg)

        assert mock_intelligence.context["system_mode"] == "autonomous"

    @patch("api.ha_connectivity.mqtt")
    def test_on_message_unknown_topic(self, mock_mqtt, mock_config):
        """Test handling unknown topic does nothing"""
        mock_movement = Mock()

        ha = HAConnectivity(mock_config, movement=mock_movement)

        mock_msg = Mock()
        mock_msg.topic = "freenove_dog/robot_dog_01/cmd/unknown"
        mock_msg.payload = b"value"

        ha.on_message(None, None, mock_msg)

        mock_movement.set_gait.assert_not_called()

    @patch("api.ha_connectivity.mqtt")
    def test_disconnect(self, mock_mqtt, mock_config):
        """Test disconnect stops loop and disconnects"""
        ha = HAConnectivity(mock_config)
        mock_client_instance = Mock()
        mock_mqtt.Client.return_value = mock_client_instance

        ha.client = mock_client_instance
        ha.disconnect()

        mock_client_instance.loop_stop.assert_called_once()
        mock_client_instance.disconnect.assert_called_once()

    @patch("api.ha_connectivity.mqtt")
    def test_publish_state_threaded(self, mock_mqtt, mock_config):
        """Test threaded publishing for heavy payloads"""
        import threading

        ha = HAConnectivity(mock_config)
        mock_client_instance = Mock()
        mock_client_instance.is_connected.return_value = True
        mock_mqtt.Client.return_value = mock_client_instance

        ha.client = mock_client_instance

        original_threads = threading.active_count()
        ha.publish_state("map", {"data": "heavy"}, use_thread=True)

        import time

        time.sleep(0.1)

        assert threading.active_count() >= original_threads


class TestMQTTIntegration:
    def test_full_state_update_flow(self, mqtt_config):
        """Test complete flow: config -> manager -> topic -> publish"""
        manager = MQTTManager(mqtt_config)

        topic = manager.get_topic("state", "battery")
        assert topic == "freenove_dog/robot_dog_01/state/battery"

        payload = manager.generate_discovery_payload(
            "sensor", "battery", "Battery", "V"
        )
        assert payload["state_topic"] == topic

    def test_discovery_topic_matches_state_topic(self, mqtt_config):
        """Verify discovery topics align with state topics"""
        manager = MQTTManager(mqtt_config)

        state_topic = manager.get_topic("state", "battery")
        discovery_topic = manager.get_discovery_topic("sensor", "battery")

        assert "robot_dog_01" in state_topic
        assert "robot_dog_01" in discovery_topic
        assert "battery" in state_topic
        assert "battery" in discovery_topic

    def test_command_topic_routing(self, mqtt_config):
        """Test command topic structure for routing"""
        manager = MQTTManager(mqtt_config)

        gait_cmd = manager.get_topic("cmd", "gait")
        mode_cmd = manager.get_topic("cmd", "system_mode")

        assert gait_cmd == "freenove_dog/robot_dog_01/cmd/gait"
        assert mode_cmd == "freenove_dog/robot_dog_01/cmd/system_mode"
        assert "cmd/" in gait_cmd
        assert "cmd/" in mode_cmd
