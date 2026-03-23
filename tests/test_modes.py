import pytest
from brain.behaviors import SecurityMonitor, AlarmPulse
from brain.bt_core import Sequence
from sal.mock_drivers import MockGait


@pytest.fixture
def mock_gait():
    return MockGait()


@pytest.fixture
def base_context(mock_gait):
    return {
        "system_mode": "autonomous",
        "gait": mock_gait,
        "sensors": {},
        "last_object_detection": None,
        "last_gesture": None,
    }


def test_security_monitor_inactive_in_home_mode(base_context):
    base_context["system_mode"] = "home"
    base_context["last_object_detection"] = {"label": "person"}
    sm = SecurityMonitor("SM", base_context)
    assert sm.run() is False


def test_security_monitor_active_in_alarm_mode(mock_gait):
    context = {
        "system_mode": "alarm",
        "last_object_detection": {"label": "person"},
        "gait": mock_gait,
        "sensors": {},
    }
    sm = SecurityMonitor("SM", context)
    assert sm.run() is True
    # When intruder is far (2000mm > pursuit_dist 600mm), should pursue
    assert mock_gait.target_speed > 0.0


def test_alarm_branch_logic(mock_gait):
    context = {
        "system_mode": "alarm",
        "last_object_detection": {"label": "person"},
        "gait": mock_gait,
        "sensors": {},
    }
    sm = SecurityMonitor("SM", context)
    ap = AlarmPulse("AP", context)

    branch = Sequence("AlarmBranch", [sm, ap])

    # Should succeed because both children succeed in alarm mode with person
    assert branch.run() is True


def test_alarm_branch_fails_in_home_mode(mock_gait):
    context = {
        "system_mode": "home",
        "gait": mock_gait,
        "sensors": {},
        "last_object_detection": None,
    }
    sm = SecurityMonitor("SM", context)
    ap = AlarmPulse("AP", context)

    branch = Sequence("AlarmBranch", [sm, ap])

    # Should fail because SecurityMonitor returns False in home mode
    assert branch.run() is False
