# Agent Instructions - Copilot

You are assisting with the Freenove Robot Dog 2.0 project. This project contains Python code for a quadruped robot with IK, behavior trees, and vision.

## Project Structure
```
main.py              # 100Hz control loop
brain/               # AI, BT, vision, social memory
movement/            # IK, gait sequencer
sal/                 # Hardware abstraction (mock/real)
api/                 # Flask, MQTT, Home Assistant
utils/               # Config, plugin loader
config/config.yaml   # All settings
tests/               # pytest test suite
```

## Critical Rules
1. I2C access only in main loop (no race conditions)
2. Set `simulation_mode: true` in config.yaml to test without hardware
3. Use `pytest` for testing

## Commands
```bash
python -m pytest tests/ -v
python main.py
```
