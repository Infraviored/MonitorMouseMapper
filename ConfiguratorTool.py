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
            self.calculate_and_apply_center_offsets()
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
        self.calculate_and_apply_center_offsets()

    def calculate_and_apply_center_offsets(self):
        """Calculates and updates monitor x_offsets to center them horizontally relative to each other.
        The wider monitor's x_offset is set to 0.
        The narrower monitor's x_offset is set to (wider_width - narrower_width) // 2.
        """
        if not hasattr(self, 'top_monitor') or not hasattr(self, 'bottom_monitor'):
            print("Warning: Top or bottom monitor not selected. Cannot apply centering.")
            return

        top_mon_orig = self.top_monitor
        bottom_mon_orig = self.bottom_monitor

        # Store original offsets before modification
        original_offsets = {m['name']: m['x_offset'] for m in self.available_monitors}

        # Find the dictionaries in the main list to update them directly
        top_mon_dict = next((m for m in self.available_monitors if m['name'] == top_mon_orig['name']), None)
        bottom_mon_dict = next((m for m in self.available_monitors if m['name'] == bottom_mon_orig['name']), None)

        if not top_mon_dict or not bottom_mon_dict:
             print(f"Warning: Could not find top or bottom monitor in available monitors list.")
             return

        # Determine wider and narrower monitors
        if top_mon_dict['width'] >= bottom_mon_dict['width']:
            wider_mon_dict = top_mon_dict
            narrower_mon_dict = bottom_mon_dict
        else:
            wider_mon_dict = bottom_mon_dict
            narrower_mon_dict = top_mon_dict

        wider_width = wider_mon_dict['width']
        narrower_width = narrower_mon_dict['width']

        # Calculate the new offset for the narrower monitor
        narrower_new_x_offset = (wider_width - narrower_width) // 2
        wider_new_x_offset = 0 # Wider monitor is always at 0 relative offset

        # Apply the new offsets to the top/bottom pair
        print(f"Applying relative horizontal centering:")
        print(f" - Wider monitor ({wider_mon_dict['name']}): Original x_offset={original_offsets[wider_mon_dict['name']]}, New x_offset={wider_new_x_offset}")
        wider_mon_dict['x_offset'] = wider_new_x_offset

        print(f" - Narrower monitor ({narrower_mon_dict['name']}): Original x_offset={original_offsets[narrower_mon_dict['name']]}, New x_offset={narrower_new_x_offset}")
        narrower_mon_dict['x_offset'] = narrower_new_x_offset

        # --- Adjust other monitors relative to the top monitor's change --- 
        # Calculate the change in the top monitor's offset
        original_top_x = original_offsets[top_mon_dict['name']]
        new_top_x = top_mon_dict['x_offset'] # This is already updated
        top_offset_delta = new_top_x - original_top_x
        
        if top_offset_delta != 0:
             print(f"Adjusting other monitors relative to top monitor ({top_mon_dict['name']}) offset change ({top_offset_delta:+d}):")
             for mon_dict in self.available_monitors:
                 # Skip the top and bottom monitors themselves
                 if mon_dict['name'] == top_mon_dict['name'] or mon_dict['name'] == bottom_mon_dict['name']:
                     continue
                 
                 original_other_x = original_offsets[mon_dict['name']]
                 new_other_x = original_other_x + top_offset_delta
                 print(f" - Monitor ({mon_dict['name']}): Original x_offset={original_other_x}, New x_offset={new_other_x}")
                 mon_dict['x_offset'] = new_other_x
        # --- End adjustment --- 

        # Note: The y_offsets are not modified by this function.
        # This only affects the configuration saved, not the live xrandr setup.

    def create_config(self):
        # This will now use the self.available_monitors list which might have updated x_offsets
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
            "edge_mapping": input("Enable edge mapping? (Y/N): ").upper() == "Y"
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
