#!/bin/bash
# Setup Script for Freenove Robot Dog Service
# Usage: chmod +x setup_service.sh && ./setup_service.sh

set -e

INSTALL_DIR="/home/pi/Freenove_Robot_New"
SERVICE_FILE="deploy/freenove_dog.service"
SERVICE_DEST="/etc/systemd/system/freenove_dog.service"

echo "=========================================="
echo "Freenove Robot Dog Service Setup"
echo "=========================================="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo:"
    echo "  sudo $0"
    exit 1
fi

# Check if directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Error: $INSTALL_DIR does not exist"
    echo "Please clone the repository first:"
    echo "  git clone <repo-url> $INSTALL_DIR"
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: $SERVICE_FILE not found"
    exit 1
fi

# Create logs directory
mkdir -p "$INSTALL_DIR/logs"
chown pi:pi "$INSTALL_DIR/logs"

# Copy service file
echo "Installing systemd service..."
cp "$SERVICE_FILE" "$SERVICE_DEST"
chmod 644 "$SERVICE_DEST"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "Enabling service..."
systemctl enable freenove_dog

# Ask for simulation mode
echo ""
echo "=========================================="
echo "Configuration"
echo "=========================================="
read -p "Run in simulation mode? [Y/n]: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Setting hardware mode (SIMULATION_MODE=false)"
    sed -i 's/Environment="SIMULATION_MODE=true"/Environment="SIMULATION_MODE=false"/' "$SERVICE_DEST"
else
    echo "Simulation mode enabled by default"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Commands:"
echo "  Start:    sudo systemctl start freenove_dog"
echo "  Stop:     sudo systemctl stop freenove_dog"
echo "  Status:   sudo systemctl status freenove_dog"
echo "  Logs:     journalctl -u freenove_dog -f"
echo ""
