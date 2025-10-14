#!/bin/bash
set -e

# This script is executed on the remote server.

# 1. Navigate to the project directory.
echo "--- Navigating to project directory... ---"
cd /home/spacexplorer11/word_ban

# 2. Pull the latest code.
echo "--- Pulling latest code... ---"
git pull

# 3. Create virtual environment if it doesn’t exist.
echo "--- Setting up Python virtual environment... ---"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# 4. Install dependencies.
echo "--- Installing dependencies... ---"
./.venv/bin/python -m pip install -r requirements.txt

# 5. Set up the systemd user service.
echo "--- Creating systemd service file... ---"
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/slack-bot.service <<EOF
[Unit]
Description=Word BAN Slack Bot

[Service]
WorkingDirectory=%h/word_ban
EnvironmentFile=%h/word_ban/.env
ExecStart=%h/word_ban/.venv/bin/python app.py
Restart=on-failure

[Install]
WantedBy=default.target
EOF

# Setting up stupid and weird env variables??
echo "Setting up stupid and weird env variables??"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"

# 6. Reload systemd and restart the service.
echo "--- Reloading systemd and restarting service... ---"
loginctl enable-linger $(whoami) || true
systemctl --user daemon-reload
systemctl --user enable --now slack-bot.service

echo "--- Deployment successful! ---"
