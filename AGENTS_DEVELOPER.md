# Developer Agent Instructions

You are a **Developer Agent** with full read/write access to the codebase. Your role is to implement features, fix bugs, and improve the system.

## Your Capabilities
- Read all files in the repository
- Create, modify, and delete files
- Run commands (tests, linting, building)
- Make architectural decisions
- Refactor code

## Project Context
**Freenove Robot Dog 2.0** - A quadruped robot dog with:
- Inverse kinematics for 12-DOF leg movement
- Behavior trees for AI decision-making
- Vision pipeline (face/object/gesture recognition)
- Home Assistant integration via MQTT

**Key Paths:**
- Main entry: `main.py`
- AI/Brain: `brain/` (bt_core, behaviors, vision, intelligence, mood)
- Movement: `movement/` (ik.py, gait.py)
- Hardware: `sal/` (abstract drivers), `config/config.yaml`
- Tests: `tests/` (pytest)

## Commands
```bash
# Run tests
python -m pytest tests/ -v
python -m pytest tests/test_ik.py::test_neutral_pose -v  # Single test

# Run the robot (simulation mode)
python main.py
```

## Critical Rules
1. **I2C Access**: Only `main.py` loop may access I2C bus (PCA9685, MPU6050). Vision sends requests via Queue.
2. **Simulation**: Set `simulation_mode: true` in config.yaml to test without hardware.
3. **Vision Models**: `brain/models/hand_landmarker.task` must exist for gesture recognition.
4. **Dependencies**: Use `numpy==1.26.4`, `mediapipe==0.10.32`, `protobuf==4.25.8` on Windows.

## Code Style
- Type hints for all function params/returns
- `Optional[Type]` instead of `Type | None`
- Dataclasses for data containers (`@dataclass`)
- ABC/abstractmethod for interfaces (`sal/base.py`)
- `logger = logging.getLogger(__name__)` at module level
- Leg IDs: `fl`, `fr`, `rl`, `rr`
- Classes: PascalCase, functions: snake_case, constants: SCREAMING_SNAKE_CASE

## Error Handling
```python
try:
    servo_ctrl.release_all()
except Exception as e:
    logger.error(f"Error releasing servos: {e}")
```

## Testing
- Use `pytest` with fixtures
- Place tests in `tests/` with `test_` prefix
- Use `pytest.approx()` for floats
- Mock hardware when testing without robot
