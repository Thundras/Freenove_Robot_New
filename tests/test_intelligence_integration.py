import pytest
from utils.config import ConfigManager
from brain.intelligence import IntelligenceController
from sal.mock_drivers import MockGait, MockBuzzer, MockLed, MockUltrasonic, MockServoController

def test_intelligence_controller_initialization():
    """
    Test that the full IntelligenceController can be instantiated.
    This guarantees that all imported behaviors in intelligence.py 
    actually exist in behaviors.py and have matching signatures.
    """
    config = ConfigManager()
    gait = MockGait()
    servo_ctrl = MockServoController()
    sensors = {
        "buzzer": MockBuzzer(),
        "led": MockLed(),
        "ultrasonic": MockUltrasonic()
    }
    
    # If a behavior (like ReactToPerson) is missing from behaviors.py,
    # this constructor will raise an ImportError or NameError.
    controller = IntelligenceController(
        config=config, 
        sensors=sensors, 
        gait=gait, 
        servo_ctrl=servo_ctrl
    )
    
    assert controller is not None
    assert controller.root is not None
    assert controller.context["system_mode"] == "autonomous"
