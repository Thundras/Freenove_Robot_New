import pytest
import time
from brain.behaviors import PlayWithBall, HandleGesture
from sal.mock_drivers import MockGait, MockBuzzer, MockLed
from movement.ik import IKEngine

@pytest.fixture
def context():
    gait = MockGait() # Assuming MockGait has necessary methods
    buzzer = MockBuzzer()
    led = MockLed()
    return {
        "gait": gait,
        "sensors": {
            "buzzer": buzzer,
            "led": led
        },
        "system_mode": "autonomous",
        "last_object_detection": None,
        "last_gesture": None
    }

def test_play_with_ball_logic(context):
    behavior = PlayWithBall("TestPlay", context)
    
    # 1. No ball detected
    assert behavior.run() is False
    
    # 2. Ball far away
    context["last_object_detection"] = {"label": "ball", "dist": 2000, "center_x": 0.5}
    assert behavior.run() is True
    # Should walk fast (0.5)
    # Note: MockGait needs to support set_target_speed
    
    # 3. Ball close (Nudge)
    context["last_object_detection"] = {"label": "ball", "dist": 300, "center_x": 0.5}
    assert behavior.run() is True
    # Should set playful pose

def test_led_animation_calls(context):
    led = context["sensors"]["led"]
    # We test the interface works without crashing
    led.animate("spin", (0, 255, 0))
    led.animate("breathe", (0, 0, 255))
    led.animate("scanner", (255, 0, 0))

def test_buzzer_feedback_on_gesture(context):
    buzzer = context["sensors"]["buzzer"]
    behavior = HandleGesture("TestGesture", context)
    
    context["last_gesture"] = {"label": "SIT"}
    # This should trigger a beep and change mode
    assert behavior.run() is True
    assert context["system_mode"] == "sit"

def test_ik_integration_math():
    ik = IKEngine()
    # Test a point that was causing issues or is standard
    angles = ik.calculate_angles(0, 90, 0)
    assert angles.coxa == 90
    assert angles.femur < 0
    assert angles.tibia > 0
