#!/usr/bin/env python3

import os
import subprocess
import time


def install_service():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    monitor_mapper_path = os.path.join(script_dir, "MonitorMouseMapper.py")

    service_content = f"""[Unit]
Description=Monitor Mouse Mapper Service
After=graphical.target

[Service]
ExecStart=/usr/bin/python3 {monitor_mapper_path}
Restart=on-failure
RestartSec=5
User={os.getlogin()}
Environment=DISPLAY=:0
StandardOutput=journal
StandardError=journal
# Add these lines for better logging
WorkingDirectory={os.path.dirname(monitor_mapper_path)}
ExecStartPre=/bin/sh -c 'echo "Starting Monitor Mouse Mapper at $(date)" >> /tmp/monitor_mouse_mapper.log'
ExecStopPost=/bin/sh -c 'echo "Stopped Monitor Mouse Mapper at $(date)" >> /tmp/monitor_mouse_mapper.log'

[Install]
WantedBy=graphical.target
"""

    service_file = "/etc/systemd/system/monitor-mouse-mapper.service"

    try:
        with open("monitor-mouse-mapper.service", "w") as f:
            f.write(service_content)

        subprocess.run(
            ["sudo", "mv", "monitor-mouse-mapper.service", service_file], check=True
        )
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(
            ["sudo", "systemctl", "enable", "monitor-mouse-mapper.service"], check=True
        )
        subprocess.run(
            ["sudo", "systemctl", "start", "monitor-mouse-mapper.service"], check=True
        )

        print("Monitor Mouse Mapper service has been installed and started.")
        print(
            "You can check its status with: sudo systemctl status monitor-mouse-mapper.service"
        )
        print(
            "For more detailed logs, check: sudo journalctl -u monitor-mouse-mapper.service"
        )
        print("Additional logs can be found in: /tmp/monitor_mouse_mapper.log")

        # Add a small delay before checking the status
        time.sleep(2)

        subprocess.run(
            ["sudo", "systemctl", "status", "monitor-mouse-mapper.service"], check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error installing or starting service: {e}")
        print("Checking service logs...")
        subprocess.run(
            [
                "sudo",
                "journalctl",
                "-u",
                "monitor-mouse-mapper.service",
                "--no-pager",
                "-n",
                "20",
            ]
        )
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    install_service()
