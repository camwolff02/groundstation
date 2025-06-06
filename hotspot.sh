#!/bin/bash

# --- Configuration ---
# Replace with your desired SSID (network name) and password.
# The password must be at least 8 characters long.
SSID="cpss"
PASSWORD="spacetime"
# --- End of Configuration ---

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root. Please use sudo." >&2
  exit 1
fi

# Validate SSID and password
if [ "$SSID" == "<Your_SSID>" ] || [ "$PASSWORD" == "<Your_Password>" ]; then
    echo "Please edit the script and set your desired SSID and PASSWORD."
    exit 1
fi

if [ ${#PASSWORD} -lt 8 ]; then
    echo "The password must be at least 8 characters long."
    exit 1
fi

# Define the systemd service name
SERVICE_NAME="hotspot.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"

# Create the systemd service file
echo "Creating systemd service file at $SERVICE_FILE..."

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Start Wi-Fi Hotspot on boot
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/nmcli device wifi hotspot ssid "$SSID" password "$PASSWORD"
ExecStop=/usr/bin/nmcli connection down "Hotspot"

[Install]
WantedBy=multi-user.target
EOF

# Reload the systemd daemon to recognize the new service
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service to start on boot
echo "Enabling hotspot service to start on boot..."
systemctl enable "$SERVICE_NAME"

# Start the service immediately
echo "Starting hotspot service now..."
systemctl start "$SERVICE_NAME"

echo "✅ Hotspot service installed and started successfully!"
echo "Your hotspot SSID is: $SSID"
