# Project Reference: Freenove Robot Dog 2.0

> [!IMPORTANT]
> **CRITICAL MAINTENANCE RULES (STRICTLY REQUIRED):**
> 1. **NEVER OVERWRITE OR DELETE**: Do not remove existing information, even if it is outdated.
> 2. **STRIKETHROUGH ONLY**: Use ~~strikethrough~~ to mark information that is no longer accurate.
> 3. **APPEND NEW INFO**: Add new architectural or technical details below or next to the struck-through content.
> 4. **KEEP ALIVE**: This document is the robot's "living memory" and must be updated with every major change.

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

> [!IMPORTANT]
> **Local Leg Frame**: Coordinate (0,0,0) for each leg is its **Shoulder Joint**. 
> - **X**: Forward/Backward
> - **Y**: Vertical (Positive is DOWN from shoulder)
> - **Z**: Lateral Sway (0 is neutral alignment with shoulder)

| Joint | Physical Axis | 90-90-90 Stance (L-Shape) | 180° Position |
| :--- | :--- | :--- | :--- |
| **J1** | **Roll** (X) | 90° (Neutral / Perpendicular) | - |
| **J2** | **Pitch** (Z) | 90° (**Horizontal**) | 180° (Vertical Down) |
| **J3** | **Pitch** (Z) | 90° (**Vertical Down**) | 180° (**Straight / Extended**) |

### Servo Execution & Safety
- **Clamping**: Safety limits are applied at the **IK Engine** level using `limit_neg/limit_pos`.
- **Driver Layer**: Maps IK angles to pulses: `middle + (ik_angle - 90)`. 
- **Mirroring**: Left-side legs are handled by the driver/config (inversion) but visualized as **mirrored** in the dashboard for side-profile comparison.
- **Source of Truth**: The `PCA9685Driver` maintains the active `current_angles` state, which is the direct source for the Dashboard's "Live Sync".

## 3. Movement & Gait Control
- **6-DOF Control**: Body can translate (x,y,z) and rotate (roll,pitch,yaw). Order: Yaw -> Pitch -> Roll.
- **Motion Blending**: ~~All pose and speed targets are ramped (MM/Deg per sec) for fluid motion.~~ All pose targets use **Organic S-Curve Smoothing** (Ease-in/out). Speed scales sinusoidally based on distance to target, preventing mechanical jerk.
- **Automatic CoM Shift**: ~~The trunk dynamically compensates for pitch angles to maintain static stability. Shift: `X_offset = height * sin(pitch) * 0.8`.~~ => The trunk dynamically compensates in 2D (X and Z) to maintain static stability. Pitch shift: `X = height * sin(pitch) * 0.8`. Roll shift: `Z = -height * sin(roll) * 0.8`.
- **IMU Auto-Leveling (Body Gimbal)**: A reactive behavior node (`AutoLevel`) applies counter-rotations to the trunk based on MPU6050 data, keeping the body level regardless of terrain slope.
- **Organic Refinements (Phase 4)**:
  - **Auto-Lean**: Body rolls into turns (`Lean = -TurnRate * 10°`) for a more dynamic, "leaning" look.
  - **Expressive Body Gaze**: Behaviors can use `set_look_at(yaw, pitch)` to peer at targets using the 6-DOF trunk, complementing head movements for deeper "presence".
- **Gaits**: 
  - **Walk**: 4-beat stable gait (FL:0.0, FR:0.5, RL:0.75, RR:0.25).
  - **Trot**: 2-beat diagonal gait (FL:0.0, FR:0.5, RL:0.5, RR:0.0).

## 4. Intelligence & Personality (Behavior DNA)
The robot's decision logic is driven by a dynamic, YAML-configurable **Behavior Tree (BT)**.

- **Dynamic DNA (`behaviors.yaml`)**: The entire tree is defined in an external config, allowing for real-time personality tuning.
- **Weighted Selection**: Decisions can be stochastic (e.g., "70% Explore, 30% Sniff"), making behavior feel organic and unpredictable.
- **Sensor Inhibition**: Behaviors can actively "mask" robot features (e.g., the robot ignores ball detection while in Security Mode).
- **Secondary Emotions**: Naturalistic layers (breathing, shivering, joy) are additive and blended on top of any active pose via the GaitSequencer.
- **Spatial Politeness**: The robot uses `MappingManager.is_safe_spot()` to ensure it only sits or lies down in "safe" (out-of-the-way) locations.
- **Short-term Memory**: The robot remembers seen persons/objects for up to **10 seconds** after they leave the field of view.

### Vision AI
- **Gestures**: `COME` (3+ fingers), `SIT` (2), `DOWN` (1), `AWAY` (0). Gated by `gesture_trust_threshold`.
- **Stabilization**: DIS assumes 45° FOV. Tilt-servo compensates for body pitch to keep gaze level. This works in tandem with **Body Auto-Leveling**.

## 5. System Configuration
- **Hot-Reload**: The main loop checks `behaviors.yaml` and `config.yaml` for disk changes and reloads the brain/config automatically (on detected mtime change).
- **Pi 3+ Profile**: 50Hz Loop, 50mm SLAM resolution, and Async MQTT publishing are enforced for resource management.
