#!/usr/bin/env python3

import json
import os
import subprocess
import re
import time


class ConfiguratorTool:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.script_dir, "config.json")
        self.config_flag_file = os.path.join(self.script_dir, "config_complete.flag")
        self.config = self.load_existing_config() or {}
        self.available_monitors = self.fetch_available_monitors()

    def load_existing_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                return json.load(f)
        return None

    def fetch_available_monitors(self):
        try:
            command_output = subprocess.check_output(["xrandr", "--query"], text=True)
            monitor_info = []
            pattern = r"(\S+) connected(?: primary)? (\d+)x(\d+)\+(\d+)\+(\d+)(?: \(.*?\))? (\d+)mm x (\d+)mm"
            for line in command_output.splitlines():
                match = re.search(pattern, line)
                if match:
                    name, width, height, x_offset, y_offset, width_mm, height_mm = (
                        match.groups()
                    )
                    monitor_info.append(
                        {
                            "name": name,
                            "width": int(width),
                            "height": int(height),
                            "x_offset": int(x_offset),
                            "y_offset": int(y_offset),
                            "width_mm": int(width_mm),
                            "height_mm": int(height_mm),
                            "primary": "primary" in line,
                        }
                    )
            return monitor_info
        except Exception as e:
            print(f"Error: Could not fetch available monitors. Exception: {e}")
            exit(1)

    def setup_monitors(self):
        print("Available Monitors:")
        for i, monitor in enumerate(self.available_monitors):
            print(
                f"{i + 1}. {monitor['name']} - Resolution: {monitor['width']}x{monitor['height']}, "
                f"Offset: +{monitor['x_offset']}+{monitor['y_offset']}, "
                f"Dimension: {monitor['width_mm']}mm x {monitor['height_mm']}mm"
                f"{' (Primary)' if monitor['primary'] else ''}"
            )

        choice = input("Choose setup method: (A) Automatic / (M) Manual: ").upper()

        if choice == "A":
            self.automatic_setup()
        elif choice == "M":
            self.manual_setup()
        else:
            print("Invalid choice. Exiting.")
            exit(1)

    def automatic_setup(self):
        sorted_monitors = sorted(self.available_monitors, key=lambda m: m["y_offset"])
        self.top_monitor = sorted_monitors[0]
        self.bottom_monitor = sorted_monitors[-1]
        print(f"Automatically assigned:")
        print(f"Top monitor: {self.top_monitor['name']}")
        print(f"Bottom monitor: {self.bottom_monitor['name']}")
        confirm = input("Is this correct? (Y/N): ").upper()
        if confirm != "Y":
            print("Switching to manual setup.")
            self.manual_setup()

    def manual_setup(self):
        top_index = int(input("Select the index of your top monitor: ")) - 1
        bottom_index = int(input("Select the index of your bottom monitor: ")) - 1
        self.top_monitor = self.available_monitors[top_index]
        self.bottom_monitor = self.available_monitors[bottom_index]

    def create_config(self):
        self.config = {
            "monitors": self.available_monitors,
            "top_monitor": self.top_monitor["name"],
            "bottom_monitor": self.bottom_monitor["name"],
            "safety_region": input("Enter safety region in pixels (default 200): ")
            or "200",
            "mousespeed_factor": input("Enter mouse speed factor (default 1.0): ")
            or "1.0",
            "mouse_height": input("Enter mouse height in pixels (default 30): ")
            or "30",
        }

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)
        print(f"Configuration saved to {self.config_file}")

        # Create the config complete flag file
        with open(self.config_flag_file, "w") as f:
            f.write("Configuration complete")
    
    def restart_service(self):
        print("Restarting Monitor Mouse Mapper service...")
        try:
            # Check if service is active
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "monitor-mouse-mapper.service"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Restart or start the service
            if result.stdout.strip() == "active":
                subprocess.run(["systemctl", "--user", "restart", "monitor-mouse-mapper.service"], check=True)
                print("Service restarted successfully.")
            else:
                subprocess.run(["systemctl", "--user", "start", "monitor-mouse-mapper.service"], check=True)
                print("Service started successfully.")
                
        except subprocess.CalledProcessError as e:
            print(f"Error restarting service: {e}")
            print("You may need to manually restart the service with: systemctl --user restart monitor-mouse-mapper.service")

    def run(self):
        print("Monitor Mouse Mapper Configurator")
        self.setup_monitors()
        self.create_config()
        self.save_config()
        
        # Ask if user wants to restart the service
        restart = input("Would you like to restart the Monitor Mouse Mapper service? (Y/N): ").upper()
        if restart == "Y":
            self.restart_service()
        else:
            print("Configuration complete. You will need to restart the service manually or restart your computer.")


if __name__ == "__main__":
    configurator = ConfiguratorTool()
    configurator.run()
    # Wait for user input before closing the terminal
    input("\nPress Enter to close this window...")
