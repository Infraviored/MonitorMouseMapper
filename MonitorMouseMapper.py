#!/usr/bin/env python3

import re
import subprocess
from pynput.mouse import Controller, Listener
import json
import os
from time import sleep

global sleep_duration
sleep_duration = 0.01

global do_print
do_print = True
# Initialize mouse controller
mouse_controller = Controller()


class MonitorManager:
    def __init__(self):
        self.config = None
        self.read_or_create_config()
        self.pick_monitors()
        self.set_additional_properties()
        self.get_and_set_monitor_info()
        self.set_monitor_position()
        self.prev_y = None
        self.do_jump = True
        self.mouse_controller = Controller()
        self.run()

    def pick_monitors(self):
        available_monitors = self.fetch_available_monitors()
        self.bottom_monitor = next((monitor for monitor in self.config['bottom_monitors'] if monitor in available_monitors), None)
        self.top_monitor = next((monitor for monitor in self.config['top_monitors'] if monitor in available_monitors), None)
        if self.bottom_monitor is None or self.top_monitor is None:
            print("Error: No suitable monitors found.")
            exit(1)

    def fetch_available_monitors(self):
        try:
            command_output = subprocess.check_output(['xrandr', '--query'], text=True)
            monitor_lines = [line.split()[0] for line in command_output.splitlines() if "connected" in line and not "disconnected" in line]
            return monitor_lines
        except Exception as e:
            print(f"Error: Could not fetch available monitors. Exception: {e}")

            exit(1)

    def set_additional_properties(self):
        self.top_width_cm = float(self.config.get(f"{self.top_monitor}_WIDTH_CM", 62.2))
        self.bottom_width_cm = float(self.config.get(f"{self.bottom_monitor}_WIDTH_CM", 34.4))
        self.safety_region = int(self.config.get("safety_region", 200))

    def get_and_set_monitor_info(self):
        self.bottom_width, self.bottom_height, self.bottom_x_offset, self.bottom_y_offset = self.get_monitor_info(self.bottom_monitor)
        self.top_width, self.top_height, self.top_x_offset, self.top_y_offset = self.get_monitor_info(self.top_monitor)


    # Changed function
    def assign_available_monitors(self):
        available_monitors = self.fetch_available_monitors()
        self.bottom_monitor = next((monitor for monitor in self.config['bottom_monitors'] if monitor in available_monitors), None)
        self.top_monitor = self.config['top_monitor'] if self.config['top_monitor'] in available_monitors else None

# New function
    def read_or_create_config(self,):
        script_dir = os.path.dirname(os.path.abspath(__file__))

        configfile = os.path.join(script_dir, "config.json")
        # Initialize a flag to track whether the config file has changed
        config_changed = False
        available_bottom_monitor = None  # Add this line
        available_top_monitor = None  # Add this line


        # Attempt to read existing config file if it exists
        if os.path.exists(configfile):
            with open(configfile, "r") as f:
                self.config = json.load(f)

            # Fetch the list of available monitors
            available_monitors = self.fetch_available_monitors()

            # Get the list of configured bottom and top monitors
            configured_bottom_monitors = self.config.get('bottom_monitors', [])
            configured_top_monitors = self.config.get('top_monitors', [])

            # Check if any of the configured monitors are available
            available_bottom_monitor = next((monitor for monitor in configured_bottom_monitors if monitor in available_monitors), None)
            available_top_monitor = next((monitor for monitor in configured_top_monitors if monitor in available_monitors), None)

            # If at least one top and one bottom monitor are available, assign them
            if available_bottom_monitor is not None and available_top_monitor is not None:
                print(f"Config read from {configfile}: {self.config}")
                self.bottom_monitor = available_bottom_monitor
                self.top_monitor = available_top_monitor
                return
            else:
                print("One or more monitors specified in the config are not connected.")
        else:
            print("No existing config file found.")
            self.config = {}  # Initialize an empty config dictionary
            config_changed = True

        # If the code reaches this point, it means either the config file didn't exist, or it did not have valid monitor configurations
        available_monitors = self.fetch_available_monitors()
        print("Available Monitors:")
        for i, monitor in enumerate(available_monitors):
            print(f"{i + 1}. {monitor}")

        # Update or set the bottom monitor if it is missing or not available
        if not available_bottom_monitor:
            bottom_monitor_index = input("Select the index of your bottom monitor from the list above: ")
            selected_bottom_monitor = available_monitors[int(bottom_monitor_index) - 1]
            if "bottom_monitors" not in self.config:
                self.config["bottom_monitors"] = []
            self.config["bottom_monitors"].append(selected_bottom_monitor)
            config_changed = True

        # Update or set the top monitor if it is missing or not available
        if not available_top_monitor:
            top_monitor_index = input("Select the index of your top monitor from the list above: ")
            selected_top_monitor = available_monitors[int(top_monitor_index) - 1]
            if "top_monitors" not in self.config:
                self.config["top_monitors"] = []
            self.config["top_monitors"].append(selected_top_monitor)
            config_changed = True


        # If the config has changed, update other settings and save the new config
        if config_changed:
            for monitor in self.config["bottom_monitors"]:
                if f"{monitor}_WIDTH_CM" not in self.config:
                    width_cm = input(f"Enter the width in cm of {monitor}: ")
                    self.config[f"{monitor}_WIDTH_CM"] = width_cm

            for monitor in self.config["top_monitors"]:
                if f"{monitor}_WIDTH_CM" not in self.config:
                    width_cm = input(f"Enter the width in cm of {monitor}: ")
                    self.config[f"{monitor}_WIDTH_CM"] = width_cm

            if "safety_region" not in self.config:
                self.config["safety_region"] = input("Enter the safety region in pixels (default: 200): ") or "200"

            # Save the updated config to the file
            with open(configfile, "w") as f:
                json.dump(self.config, f)

            print(f"New config created: {self.config}")

        # Assign the first available bottom and top monitors
        self.bottom_monitor = next((monitor for monitor in self.config['bottom_monitors'] if monitor in available_monitors), None)
        self.top_monitor = next((monitor for monitor in self.config['top_monitors'] if monitor in available_monitors), None)



    def get_monitor_info(self, monitor):
        """Fetch the monitor details using xrandr and return them."""
        try:
            command_output = subprocess.check_output(
                ['xrandr', '--query'], text=True)
            monitor_line = [line for line in command_output.splitlines() if monitor in line and "connected" in line][0]
            resolution_info = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', monitor_line).groups()
            return tuple(map(int, resolution_info))
        except Exception as e:
            print(f"Error: Could not find resolution info for {monitor}. Exception: {e}")
            exit(1)

    def set_monitor_position(self):
        """Set the monitor position using xrandr."""
        new_bottom_x_offset = (self.top_width - self.bottom_width) // 2 + self.top_x_offset  # Used class attributes
        new_bottom_y_offset = self.top_height  # Used class attribute
        print(f"Setting {self.bottom_monitor} position to {new_bottom_x_offset}x{new_bottom_y_offset}")
        subprocess.run(['xrandr', '--output', self.bottom_monitor, '--pos', f"{new_bottom_x_offset}x{new_bottom_y_offset}"])

    def supervise_mouse_position(self, x, y):
        """Print the mouse position and handle jumps when crossing monitor boundaries."""
        if do_print:
            print(f"\r X: {x}, Y: {y}", end="   ", flush=True)

        if abs(y - self.top_height) >= int(self.config["safety_region"]):  # Used class attribute
            return

        if self.do_jump and self.prev_y is not None:
            if (y >= self.top_height and self.prev_y < self.top_height) or (y < self.top_height and self.prev_y >= self.top_height):  # Used class attribute
                direction = 'down' if y >= self.top_height else 'up'  # Used class attribute
                new_x = self.handle_jump(x, direction)
                self.mouse_controller.position = (new_x, y)  # Assumed that mouse_controller is also a class attribute
                print(f"jumped {direction}".upper())

        self.prev_y = y


    def handle_jump(self, old_x, direction):
        top_dpi = self.top_width / self.top_width_cm
        bottom_dpi = self.bottom_width / self.bottom_width_cm
        top_mid = self.top_width // 2
        bottom_x_offset = top_mid - (self.bottom_width // 2)
        bottom_mid = (self.bottom_width // 2) + bottom_x_offset
        offset = old_x - (top_mid if direction == 'up' else bottom_mid)
        scaling_factor = bottom_dpi / top_dpi if direction == 'down' else top_dpi / bottom_dpi
        new_offset = offset * scaling_factor
        new_x = (bottom_mid if direction == 'down' else top_mid) + new_offset
        return new_x


    def run(self):
        with Listener(on_move=self.supervise_mouse_position) as listener:
            listener.join()

if __name__ == "__main__":
    monitor_manager = MonitorManager()