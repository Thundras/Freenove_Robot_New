#!/bin/bash

# Freenove Robot Dog 2.0 - Setup Script
# Run this on a fresh Raspberry Pi OS (Bullseye/Bookworm)

set -e

echo "🚀 Starting Freenove Robot Dog Setup..."

# 1. Update System
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# 2. Install System Dependencies
echo "🛠️ Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    libgl1-mesa-glx \
    libv4l-dev \
    i2c-tools \
    libatlas-base-dev \
    libopenblas-dev

# 3. Enable Hardware Interfaces
echo "⚙️ Enabling I2C and Camera..."
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_camera 0

# 4. Setup Python Environment
echo "🐍 Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

echo "pip Installing Python dependencies (this may take a few minutes)..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Setup Systemd Service
echo "🕒 Configuring systemd service..."
# Detect current directory
CUR_DIR=$(pwd)
SERVICE_FILE="freenove_dog.service"

# Update path in service file
sed -i "s|WORKING_DIR|$CUR_DIR|g" $SERVICE_FILE

sudo cp $SERVICE_FILE /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable freenove_dog.service

echo "✅ Setup Complete!"
echo "To start the robot, run: sudo systemctl start freenove_dog"
echo "To check logs, run: journalctl -u freenove_dog -f"
