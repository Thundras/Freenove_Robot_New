# Agent Instructions for Freenove Robot Dog Project

## Project Overview
This is a Python project for a quadruped robot dog controlled by a Raspberry Pi. The robot uses inverse kinematics for leg movement, behavior trees for AI decision-making, and has a vision pipeline for face/object recognition.

**Hardware Specs:**
- 12x ES08MA II servos (3 per leg: hip, femur, tibia)
- 1x S90 servo for head
- 7x WS2812 NeoPixel LEDs
- 1x active buzzer
- MPU6050 IMU (I2C)
- HC-SR04 ultrasonic sensor (GPIO)
- ADS7830 battery monitor (I2C)
- OV5647 camera (CSI)
- PCA9685 16-channel PWM driver (I2C)

**Key modules:**
- `main.py` - Main control loop (50-100Hz), initializes all components
- `brain/` - Behavior trees, vision pipeline, social memory, mood system
- `movement/` - Inverse kinematics (IK) and gait sequencer
- `sal/` - Hardware abstraction layer (mock/real drivers)
- `api/` - Flask web server, MQTT, Home Assistant connectivity
- `utils/` - Configuration manager, plugin loader
- `config/` - YAML configuration files

## Critical Architecture Rules

### I2C Bus Safety
**IMPORTANT:** I2C bus access (PCA9685, MPU6050, ADS7830) is ONLY permitted through the main loop. The Vision pipeline sends requests via Queue - the IntelligenceController processes them safely. This prevents I2C contention and race conditions.

### Simulation Mode
Set `simulation_mode: true` in config.yaml to run without hardware. All drivers are mocked and actions are logged instead of sent to hardware.

### Vision Models Required
The `brain/models/` directory must contain:
- `hand_landmarker.task` - Download from MediaPipe models

## Build, Test, and Lint Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/

# Run a specific test file
python -m pytest tests/test_ik.py -v

# Run a specific test function
python -m pytest tests/test_ik.py::test_neutral_pose -v

# Run tests matching a keyword
python -m pytest tests/ -k "gait" -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=term-missing

# Run in simulation mode (requires config.yaml simulation_mode: true)
python main.py

# Single test file with verbose output
python -m pytest tests/test_sal.py -v --tb=short
```

**Note:** There are no configured lint tools (ruff, black, mypy). Python 3.10+ is required.

### Critical Dependency Versions (Windows)
- `numpy==1.26.4` - Prevents NumPy 2.0 incompatibility with MediaPipe
- `mediapipe==0.10.32` - Modern Tasks API Bundle
- `protobuf==4.25.8` - Required for TF/MediaPipe combination

## Code Style Guidelines

### General
- Use standard Python 3.10+ features (type hints, dataclasses, f-strings)
- No docstrings on private/internal methods unless the logic is complex
- Keep functions focused and single-purpose
- Use `logger = logging.getLogger(__name__)` at module level for logging

### Imports
- Standard library imports first, then third-party, then local
- Group with blank lines between groups
- Use absolute imports within the project
```python
import os
import time
import logging
from typing import Dict, List, Optional, Any

import numpy as np
import yaml

from utils.config import ConfigManager
from sal.factory import SalFactory
from movement.ik import IKEngine
```

### Naming Conventions
- Classes: `PascalCase` (e.g., `IKEngine`, `GaitSequencer`, `ConfigManager`)
- Functions/methods: `snake_case` (e.g., `calculate_angles`, `set_target_speed`)
- Variables: `snake_case` (e.g., `base_height`, `step_length`, `current_speed`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `CONTROL_LOOP_HZ`)
- Private methods/attributes: prefix with `_` (e.g., `_apply_gait`, `_eval_params`)
- Leg identifiers: `fl`, `fr`, `rl`, `rr` (front-left, front-right, rear-left, rear-right)

### Type Hints
- Use type hints for all function parameters and return values
- Use `Optional[Type]` instead of `Type | None`
- Use `Any` sparingly - prefer concrete types
```python
def calculate_angles(self, x: float, y: float, z: float, limits: Optional[dict] = None) -> LegAngles:
def get_data(self) -> Optional[SensorData]:
```

### Dataclasses
- Use `@dataclass` for simple data containers (SensorData, LegAngles, etc.)
```python
from dataclasses import dataclass

@dataclass
class LegAngles:
    joint_1: float
    joint_2: float
    joint_3: float
```

### Interfaces and ABC
- Use `ABC` and `@abstractmethod` for interface definitions in `sal/base.py`
```python
from abc import ABC, abstractmethod

class ISensor(ABC):
    @abstractmethod
    def update(self) -> None:
        pass

    @abstractmethod
    def get_data(self) -> Optional[SensorData]:
        pass
```

### Error Handling
- Use specific exception types when possible
- Wrap hardware/simulation fallbacks in try/except with logging
- Never let exceptions propagate silently in the main loop
```python
try:
    servo_ctrl.release_all()
except Exception as e:
    logger.error(f"Error releasing servos: {e}")
```

### Logging
- Use the standard `logging` module
- Log levels: DEBUG (details), INFO (normal operations), WARNING, ERROR, CRITICAL
- Include context in log messages: `logger.info(f"Robot ready. Control Loop running at {hz}Hz.")`
- Avoid logging secrets or sensitive data

### Configuration
- All configuration is in `config/config.yaml`
- Use dot notation for nested keys: `config.get("system.control_loop_hz")`
- Support `simulation_mode: true` to run without hardware

### Testing
- Use `pytest` with fixtures
- Place tests in `tests/` directory with `test_` prefix
- Each module should have a corresponding test file
- Use `pytest.approx()` for floating-point comparisons
- Mock hardware drivers when testing without robot

### Simulation/Mock Drivers
- The SAL (System Abstraction Layer) provides mock drivers
- Set `simulation_mode: true` in config to enable
- Mock drivers log actions instead of sending to hardware
- Always check `SalFactory` for driver instantiation

### Behavior Trees
- Defined in `brain/behaviors.py` and loaded from YAML
- Node types: `Selector` (OR), `Sequence` (AND), `Parallel`, `Inverter`
- Leaf nodes: `Condition` (check), `ParameterLeaf` (action with dynamic params)
- Context dictionary shares state across all nodes

### Vision Pipeline
- Runs in a separate `multiprocessing.Process` (`VisionProcess`)
- Communicates via `Queue` with maxsize to prevent memory bloat
- Shares `Array` for IMU data and flags between processes
- Supports face recognition (SFace), object detection (YuNet), gesture recognition (MediaPipe)

### Performance Considerations
- Main loop target: 50-100Hz control frequency
- Vision processing is decoupled (runs in separate process)
- Throttle telemetry (1Hz for Home Assistant)
- Use `time.perf_counter()` for precise timing

### Git Workflow
- Do NOT modify original code in `Freenove_Robot_Dog_Kit_for_Raspberry_Pi`
- All new development goes in this repository
- Run tests before committing
- Use descriptive commit messages

### Social Memory & Trust System
- `SocialMemory` class manages face database with multi-view templates (up to 10 embeddings per person)
- Trust builds over time using cubic curve: `trust = min(1.0, (exposure / 3600.0)**3)`
- Faces stored in `brain/face_db.json`, images in `api/static/faces/`
- Garbage collection removes transient faces (<15s exposure) after 2 hours of inactivity

### Deployment (Raspberry Pi)
- Run `setup.sh` to enable I2C, Camera, and install dependencies
- Register as systemd service: `sudo systemctl start freenove_dog`
- View logs: `journalctl -u freenove_dog -f`
- Config: `config/config.yaml` (MQTT broker, servo calibration)

### Directory Structure
```
Freenove_Robot_New/
├── main.py              # Entry point
├── brain/               # AI, behavior trees, vision
│   ├── bt_core.py       # BT node definitions
│   ├── bt_factory.py    # YAML-based BT builder
│   ├── behaviors.py     # Leaf node implementations
│   ├── vision.py        # Vision subprocess
│   ├── intelligence.py  # Main AI controller
│   └── mood.py          # Emotional state
├── movement/            # Locomotion
│   ├── ik.py            # Inverse kinematics
│   └── gait.py          # Gait sequencer
├── sal/                 # Hardware abstraction
│   ├── base.py          # Interfaces
│   ├── factory.py       # Driver factory
│   ├── mock_drivers.py # Simulation drivers
│   └── *_driver.py     # Real hardware drivers
├── api/                 # External interfaces
│   ├── web_server.py    # Flask REST API
│   ├── mqtt_manager.py # MQTT client
│   └── ha_connectivity.py # Home Assistant
├── utils/
│   ├── config.py        # YAML config manager
│   └── plugin_loader.py
├── config/
│   └── config.yaml      # Configuration
└── tests/               # pytest test suite
```
