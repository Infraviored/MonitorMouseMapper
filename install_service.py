#!/usr/bin/env python3

import os
import subprocess
import sys


def install_service():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    monitor_mapper_path = os.path.join(script_dir, "MonitorMouseMapper.py")

    # Check if the MonitorMouseMapper.py file exists
    if not os.path.exists(monitor_mapper_path):
        print(f"Error: {monitor_mapper_path} does not exist.")
        return

    # Get the user ID
    user_id = os.getuid()
    
    service_content = f"""[Unit]
Description=Monitor Mouse Mapper Service
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -u {monitor_mapper_path}
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0
Environment=XAUTHORITY=%h/.Xauthority
StandardOutput=journal
StandardError=journal
WorkingDirectory={script_dir}

[Install]
WantedBy=graphical-session.target
"""

    user_service_dir = os.path.expanduser("~/.config/systemd/user")
    service_file = os.path.join(user_service_dir, "monitor-mouse-mapper.service")

    try:
        # Create user service directory if it doesn't exist
        os.makedirs(user_service_dir, exist_ok=True)

        # Write service file
        with open(service_file, "w") as f:
            f.write(service_content)

        # Reload systemd user daemon
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)

        # Stop the service if it's already running
        subprocess.run(
            ["systemctl", "--user", "stop", "monitor-mouse-mapper.service"], check=False
        )

        # Enable and start the service
        subprocess.run(
            ["systemctl", "--user", "enable", "monitor-mouse-mapper.service"],
            check=True,
        )
        subprocess.run(
            ["systemctl", "--user", "start", "monitor-mouse-mapper.service"], check=True
        )

        print(
            "Monitor Mouse Mapper service has been installed and started as a user service."
        )
        print(
            "You can check its status with: systemctl --user status monitor-mouse-mapper.service"
        )

        # Ensure pynput is installed for the user
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "pynput"], check=True
        )

        # Add DISPLAY export to .bashrc if not already present
        bashrc_path = os.path.expanduser("~/.bashrc")
        display_export = "export DISPLAY=:0"
        with open(bashrc_path, "r+") as bashrc:
            if display_export not in bashrc.read():
                bashrc.write(f"\n{display_export}\n")

        print("Please log out and log back in for all changes to take effect.")

    except subprocess.CalledProcessError as e:
        print(f"Error installing or starting service: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    install_service()
