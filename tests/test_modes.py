import pytest
from brain.behaviors import SecurityMonitor, AlarmPulse
from brain.bt_core import Sequence
from sal.mock_drivers import MockGait

def test_security_monitor_inactive_in_home_mode():
    context = {"system_mode": "home", "last_object_detection": {"label": "person"}, "sensors": {}}
    sm = SecurityMonitor("SM", context)
    assert sm.run() is False

def test_security_monitor_active_in_alarm_mode():
    gait = MockGait()
    context = {
        "system_mode": "alarm", 
        "last_object_detection": {"label": "person"},
        "gait": gait,
        "sensors": {}
    }
    sm = SecurityMonitor("SM", context)
    assert sm.run() is True
    assert gait.target_speed == 0.0

def test_alarm_branch_logic():
    gait = MockGait()
    context = {
        "system_mode": "alarm", 
        "last_object_detection": {"label": "person"},
        "gait": gait,
        "sensors": {}
    }
    sm = SecurityMonitor("SM", context)
    ap = AlarmPulse("AP", context)
    
    branch = Sequence("AlarmBranch", [sm, ap])
    
    # Should succeed because both children succeed in alarm mode with person
    assert branch.run() is True

def test_alarm_branch_fails_in_home_mode():
    context = {"system_mode": "home", "sensors": {}}
    sm = SecurityMonitor("SM", context)
    ap = AlarmPulse("AP", context)
    
    branch = Sequence("AlarmBranch", [sm, ap])
    
    # Should fail because SecurityMonitor returns False in home mode
    assert branch.run() is False
