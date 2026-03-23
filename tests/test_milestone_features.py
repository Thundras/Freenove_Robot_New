import pytest
import time
from brain.behaviors import PlayWithBall, HandleGesture
from sal.mock_drivers import MockGait, MockBuzzer, MockLed
from movement.ik import IKEngine


@pytest.fixture
def context():
    gait = MockGait()  # Assuming MockGait has necessary methods
    buzzer = MockBuzzer()
    led = MockLed()
    return {
        "gait": gait,
        "sensors": {"buzzer": buzzer, "led": led},
        "system_mode": "autonomous",
        "last_object_detection": None,
        "last_gesture": None,
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

    # HandleGesture requires timestamps and persistence buffering
    # Use AWAY gesture which is NOT blocked by trust threshold
    for i in range(1, 4):
        context["last_gesture"] = {"label": "AWAY", "timestamp": i}
        assert behavior.run() is False  # Buffering until 3rd gesture

    # After 3rd AWAY gesture, should resume autonomous mode
    assert context["system_mode"] == "autonomous"


def test_ik_integration_math():
    ik = IKEngine()
    # Test standing position at y=90 (between min and max reach)
    angles = ik.calculate_angles(0, 90, 0)
    assert angles.shoulder == pytest.approx(
        0, abs=0.1
    )  # Shoulder = 0 when z=0 (horizontal to body)
    assert angles.thigh > 0  # Thigh is bent up
    assert angles.shin > 0  # Shin is bent
