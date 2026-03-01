# 🚀 Freenove Robot Dog 2.0 - Deployment Guide

This guide describes how to install and run the robot software on your Raspberry Pi.

## 📋 Prerequisites
*   **Raspberry Pi 4B** (recommended) or 3B+.
*   **Raspberry Pi OS** (Bullseye or Bookworm, 64-bit recommended).
*   **Active Internet Connection**.
*   **Hardware Assembled** and I2C/Camera/NeoPixels connected.

---

## 🛠️ Installation in 3 Steps

### 1. Copy Files
Copy the entire `freenove_robot_new` directory to your Pi (e.g., via SCP or Git).
```bash
git clone <your-repository-url>
cd freenove_robot_new
```

### 2. Run Setup Script
The `setup.sh` script automates system updates, interface enabling (I2C/Camera), and Python environment setup.
```bash
chmod +x setup.sh
./setup.sh
```

### 3. Verification
Once the setup is complete, you can start the robot manually to verify:
```bash
source venv/bin/activate
python main.py
```

---

## ⚙️ Running as a System Service
The setup script automatically registers the robot as a `systemd` service.

*   **Start Service:** `sudo systemctl start freenove_dog`
*   **Stop Service:** `sudo systemctl stop freenove_dog`
*   **Check Status:** `sudo systemctl status freenove_dog`
*   **View Logs:** `journalctl -u freenove_dog -f`

---

## 🔧 Configuration
Most settings can be found in `utils/config.yaml`:
*   **MQTT:** Update your broker address for Home Assistant integration.
*   **Calibration:** If the legs are not aligned, update the `middle` servo offsets.

## ⚠️ Troubleshooting
*   **I2C Error:** Ensure `i2c-tools` is installed and `ls /dev/i2c-1` shows the device. Use `i2cdetect -y 1` to find addresses.
*   **Camera Error:** Ensure the ribbon cable is correctly seated and the camera is enabled in `raspi-config`.
*   **Permissions:** Always run the setup script as the `pi` user (it will use `sudo` where needed).
