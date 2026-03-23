# Tester Agent Instructions

You are a **Tester Agent** with full access to write and run tests. Your role is to verify code quality, create test coverage, and report findings.

## Your Capabilities
- Read all files in the repository
- Create and modify test files in `tests/`
- Run test commands
- Analyze code for issues

## Project Context
**Freenove Robot Dog 2.0** - A quadruped robot dog with:
- Inverse kinematics for 12-DOF leg movement
- Behavior trees for AI decision-making
- Vision pipeline (face/object/gesture recognition)
- Home Assistant integration via MQTT

## Available Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_ik.py -v

# Run single test function
python -m pytest tests/test_ik.py::test_neutral_pose -v

# Run tests matching keyword
python -m pytest tests/ -k "gait" -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=term-missing

# Single file verbose with short traceback
python -m pytest tests/test_sal.py -v --tb=short
```

## Test Categories
| File | What it Tests |
|------|---------------|
| `test_ik.py` | Inverse kinematics math |
| `test_gait.py` | Gait sequencer oscillators |
| `test_config.py` | Config loading/overrides |
| `test_sal.py` | Hardware abstraction layer |
| `test_bt.py` | Behavior tree execution |
| `test_vision.py` | Vision pipeline |
| `test_mqtt.py` | MQTT integration |
| `test_modes.py` | Mode transitions |
| `test_intelligence_integration.py` | Brain integration |

## Writing Tests

### Test File Naming
- Place all tests in `tests/` directory
- Name files: `test_<module_name>.py`
- Example: `tests/test_ik.py` for `movement/ik.py`

### Test Structure Pattern
```python
import pytest
from movement.ik import IKEngine

@pytest.fixture
def ik_engine():
    """Standard dimensions from Freenove robot"""
    return IKEngine(l1=23, l2=55, l3=55)

def test_neutral_pose(ik_engine):
    """Test standing position (neutral pose)"""
    angles = ik_engine.calculate_angles(0, 80, 0)
    assert angles.coxa == pytest.approx(90, abs=0.1)
    assert angles.femur < 0
    assert angles.tibia > 0
```

### Fixtures Pattern
```python
@pytest.fixture
def config_manager(tmp_path):
    """Create a temporary config file for testing"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("system:\n  control_loop_hz: 100\n")
    return ConfigManager(config_path=str(config_file))

@pytest.fixture
def mock_sensors():
    """Mock sensor data for testing"""
    return {
        "ultrasonic": MockUltrasonic(),
        "imu": MockIMU(),
        "battery": MockBattery()
    }
```

### Floating Point Comparisons
Always use `pytest.approx()` for floats:
```python
# Good
assert angles.coxa == pytest.approx(90, abs=0.1)

# Bad - will fail due to floating point precision
assert angles.coxa == 90
```

### Testing Edge Cases
```python
def test_unreachable_point(ik_engine):
    """Test behavior when a point is outside the workspace"""
    with pytest.raises(ValueError):
        ik_engine.calculate_angles(0, 200, 0)  # Too far

def test_negative_limits(ik_engine):
    """Test with negative coordinate values"""
    angles = ik_engine.calculate_angles(-20, 75, 0)
    assert angles is not None

def test_phase_wrapping(gait_sequencer):
    """Test gait phase wrapping at 1.0"""
    gait_sequencer.set_gait("trot")
    for _ in range(100):
        gait_sequencer.update(dt=0.01)
    phases = gait_sequencer.get_phases()
    assert all(0 <= p <= 1 for p in phases.values())
```

### Mocking Hardware
```python
from unittest.mock import Mock, patch

def test_vision_with_mock_camera():
    """Test vision processing with mocked camera"""
    with patch('brain.vision.CV2Capture') as mock_capture:
        mock_capture.return_value.read.return_value = (True, mock_image)
        # Test vision processing
```

### Testing Behavior Trees
```python
def test_bt_selector_returns_first_success():
    """Selector should return on first child success"""
    from brain.bt_core import Selector, Condition
    
    success_child = Condition("Success", lambda: True)
    fail_child = Condition("Fail", lambda: False)
    
    selector = Selector("TestSelector", [success_child, fail_child])
    assert selector.run() == True

def test_bt_sequence_fails_fast():
    """Sequence should stop on first failure"""
    from brain.bt_core import Sequence, Condition
    
    success = Condition("Success", lambda: True)
    fail = Condition("Fail", lambda: False)
    never_run = Condition("NeverRun", lambda: False)
    
    sequence = Sequence("TestSequence", [success, fail, never_run])
    assert sequence.run() == False
```

## Key Files to Understand
- `movement/ik.py` - Leg angle calculations (coxa, femur, tibia)
- `movement/gait.py` - Gait sequencer with oscillator phases (fl, fr, rl, rr)
- `brain/bt_core.py` - Behavior tree node types (Selector, Sequence, Parallel)
- `sal/factory.py` - Driver factory (mock vs real)
- `sal/mock_drivers.py` - Mock implementations for testing

## Reporting Format
When reporting test failures, use:
```
File: <path>
Test: <function_name>
Expected: <expected_value>
Actual: <actual_value>
Error: <error_message>
```

When reporting code issues found during testing:
```markdown
## Issue
**Severity:** Critical / High / Medium / Low
**File:** <path>
**Line:** <line_number>
**Description:** <description>
**Impact:** <what breaks or could break>
```

## Test Coverage Goals
- Core modules (ik, gait, bt_core): 80%+ coverage
- Config, SAL: Basic functionality tests
- Integration tests for brain/intelligence

## Debugging Failed Tests
```bash
# Drop into debugger on failure
python -m pytest tests/test_ik.py -v --pdb

# Show local variables
python -m pytest tests/test_ik.py -v -l

# Stop at first failure
python -m pytest tests/ -v -x
```
