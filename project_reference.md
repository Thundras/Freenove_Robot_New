# Project Reference: Freenove Robot Dog 2.0

> [!IMPORTANT]
> **Maintenance Rules:**
> 1. **Add Only**: append new information as the project evolves.
> 2. **No Deletions**: do not delete old information. Instead, use ~~strikethrough~~ for information that is no longer accurate.
> 3. **Keep Current**: this document must be updated whenever significant design decisions or architectural changes are made.

This document serves as the "Source of Truth" for design decisions, architecture, and hardware configurations for the Freenove Robot project.

## 1. Hardware & Connectivity
- **Core Controller**: Raspberry Pi 3+
- **Servo PWM**: PCA9685 (Address: 0x40, 50Hz)
- **IMU**: MPU6050 (Address: 0x68)
- **Sensors**: Ultrasonic HC-SR04 (Trigger: 27, Echo: 22)
- **Visual Feedback**: 8-LED WS2812B Ring (Pin 18)
- **Audio**: Active Buzzer (Pin 17)
- **Camera**: Pi Cam / USB Cam (320x240 @ 20 FPS)

## 2. Robot Geometry & Kinematics
Measurements are in **millimeters (mm)**.

### Body & Leg Segments
- **Body**: 140L x 80W. Shoulder-to-Body Offset: 50mm.
- **Legs**: L1 (Shoulder) = 25, L2 (Femur) = 55, L3 (Tibia) = 60.
- **Default Height**: **75mm** (Shoulder to Foot) - Optimized for Pi 3+ stability.

### Coordinate System (Roll-Pitch-Pitch)
| Joint | Physical Axis | 90° Stance (Neutral) | Range / Action |
| :--- | :--- | :--- | :--- |
| **J1** | **Roll** (X) | 90° (Perpendicular) | > 90°: Tilt Outwards |
| **J2** | **Pitch** (Z) | 90° (Horizontal) | > 90°: Point Downwards |
| **J3** | **Pitch** (Z) | 90° (L-shape bend) | 180°: Straight leg |

### Servo Execution & Safety
- **Clamping**: Safety limits are applied at the **IK Engine** level (for legs) and **Intelligence Layer** (for camera tilt) using `limit_neg/limit_pos`.
- **Driver Layer**: The `PCA9685Driver` maps IK angles to pulses: `middle + (ik_angle - 90)`.
- **Calibration Mode**: When `system_mode` is set to `calibrate`, the Behavior Tree is **disabled** to allow manual control and calibration without AI interference.

## 3. Movement & Gait Control
- **6-DOF Control**: Body can translate (x,y,z) and rotate (roll,pitch,yaw). Order: Yaw -> Pitch -> Roll.
- **Motion Blending**: All pose targets use **Organic S-Curve Smoothing** (Ease-in/out). Speed scales sinusoidally based on distance to target, preventing mechanical jerk.
- **Gaits**: 
  - **Walk**: 4-beat stable gait (FL:0.0, FR:0.5, RL:0.75, RR:0.25).
  - **Trot**: 2-beat diagonal gait (FL:0.0, FR:0.5, RL:0.5, RR:0.0).

## 4. Intelligence & Personality

### Behavior Tree (BT)
Atomic actions (Leafs) organized into Selectors (Priority) and Sequences (Logic).
- **Parallel Root**: Runs `ExpressMood` (Passive movement) and `ActiveLogic` (Goal-driven) concurrently.

### Mood System (`brain/mood.py`)
- **Energy**: Decays over a **2-hour period**.
- **Normalization**: Emotions (`Excitement`, `Comfort`) return to baseline at **0.005 units/sec**.
- **Baselines**: Excitement=0.3, Comfort=0.7, Aggression=0.0.

### Vision AI
- **Gestures**: `COME` (3+ fingers), `SIT` (2), `DOWN` (1), `AWAY` (0/Fist).
- **Stabilization**: DIS assumes 45° FOV. Tilt-servo compensates for body pitch to keep gaze level.

## 5. System Configuration
- **Hot-Reload**: The main loop checks `config.yaml` every **2 seconds** for disk changes and reloads automatically.
- **Pi 3+ Profile**: 50Hz Loop, 50mm SLAM resolution, and Async MQTT publishing are enforced for resource management.
