#!/usr/bin/env python3

import re
import subprocess
from pynput.mouse import Controller, Listener
import json
import os
from time import sleep
import signal
import sys
import atexit
import time


global sleep_duration
sleep_duration = 0.01

global do_print
do_print = True
# Initialize mouse controller
mouse_controller = Controller()


class MonitorManager:
    def __init__(self):
        self.pid_file = "/tmp/monitor_manager.pid"
        self.register_signal_handlers()
        self.startup_pid_check()
        self.available_monitors = self.fetch_available_monitors()
        self.config = self.read_config()
        if self.is_config_valid():
            print("Using existing configuration.")
            self.apply_config()
        else:
            print("Current setup is not configured. Launching configurator.")
            self.setup_and_confirm()
        self.run()

    def register_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        self.cleanup_pid_file()
        sys.exit(0)

    def cleanup_pid_file(self):
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
        print("Cleaned up PID file and exiting.")

    def startup_pid_check(self):
        if os.path.exists(self.pid_file):
            with open(self.pid_file, "r") as f:
                old_pid = int(f.read())
            try:
                os.kill(old_pid, 0)  # Check if process is running
                print(
                    f"An instance of the script is already running with PID {old_pid}. Stopping it."
                )
                os.kill(old_pid, signal.SIGTERM)  # Terminate the old process
                sleep(1)  # Give it some time to terminate
                # Since there was a running instance, we exit the new instance after killing the old one
                print(
                    "Terminated the old instance. Exiting the new instance to prevent duplicates."
                )
                exit()
            except OSError:
                print("No running instance found. Starting a new one.")
        else:
            print("No existing PID file found. Starting a new instance.")

        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

    def set_mousespeed(self):
        if self.config.get("mousespeed_factor") != "1.0":
            print(
                f"Setting mousespeed factor to {self.config.get('mousespeed_factor')}"
            )
            subprocess.run(
                [
                    "xinput",
                    "--set-prop",
                    self.config.get("mouse_id"),
                    self.config.get("coordinate_transformation_matrix_id"),
                    self.config.get("mousespeed_factor"),
                    "0",
                    "0",
                    "0",
                    self.config.get("mousespeed_factor"),
                    "0",
                    "0",
                    "0",
                    "1",
                ]
            )

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
        # Sort monitors by vertical position
        sorted_monitors = sorted(self.available_monitors, key=lambda m: m["y_offset"])

        self.top_monitor = sorted_monitors[0]
        self.bottom_monitor = sorted_monitors[-1]

        print(f"Automatically assigned:")
        print(
            f"Top monitor: {self.top_monitor['name']} - "
            f"Resolution: {self.top_monitor['width']}x{self.top_monitor['height']}, "
            f"Offset: +{self.top_monitor['x_offset']}+{self.top_monitor['y_offset']}, "
            f"Width: {self.top_monitor['width_mm']}mm"
        )
        print(
            f"Bottom monitor: {self.bottom_monitor['name']} - "
            f"Resolution: {self.bottom_monitor['width']}x{self.bottom_monitor['height']}, "
            f"Offset: +{self.bottom_monitor['x_offset']}+{self.bottom_monitor['y_offset']}, "
            f"Width: {self.bottom_monitor['width_mm']}mm"
        )

        confirm = input("Is this correct? (Y/N): ").upper()
        if confirm != "Y":
            print("Switching to manual setup.")
            self.manual_setup()

    def manual_setup(self):
        top_index = int(input("Select the index of your top monitor: ")) - 1
        bottom_index = int(input("Select the index of your bottom monitor: ")) - 1

        self.top_monitor = self.available_monitors[top_index]
        self.bottom_monitor = self.available_monitors[bottom_index]

    def set_additional_properties(self):
        self.bottom_width_cm = self.bottom_monitor["width_mm"] / 10
        self.top_width_cm = self.top_monitor["width_mm"] / 10

    def get_and_set_monitor_info(self):
        (
            self.bottom_width,
            self.bottom_height,
            self.bottom_x_offset,
            self.bottom_y_offset,
        ) = self.get_monitor_info(self.bottom_monitor["name"])
        self.top_width, self.top_height, self.top_x_offset, self.top_y_offset = (
            self.get_monitor_info(self.top_monitor["name"])
        )

    def read_config(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        configfile = os.path.join(script_dir, "config.json")
        if os.path.exists(configfile):
            try:
                with open(configfile, "r") as f:
                    config = json.load(f)
                print(f"Config read from {configfile}: {config}")
                return config
            except json.JSONDecodeError:
                print("Error reading config file. Creating a new one.")
        return None

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
        self.safety_region = int(self.config["safety_region"])
        self.mousespeed_factor = float(self.config["mousespeed_factor"])
        self.mouse_height = int(self.config["mouse_height"])

    def get_monitor_info(self, monitor_name):
        """Fetch the monitor details using xrandr and return them."""
        try:
            command_output = subprocess.check_output(["xrandr", "--query"], text=True)
            monitor_line = [
                line
                for line in command_output.splitlines()
                if monitor_name in line and "connected" in line
            ][0]
            resolution_info = re.search(
                r"(\d+)x(\d+)\+(\d+)\+(\d+)", monitor_line
            ).groups()
            return tuple(map(int, resolution_info))
        except Exception as e:
            print(
                f"Error: Could not find resolution info for {monitor_name}. Exception: {e}"
            )
            exit(1)

    def set_monitor_position(self):
        """Set the monitor position using xrandr."""
        new_bottom_x_offset = max(
            0, (self.top_width - self.bottom_width) // 2 + self.top_x_offset
        )
        new_bottom_y_offset = self.top_height + self.mouse_height

        # Check if the new position is different from the current position
        if (
            new_bottom_x_offset != self.bottom_x_offset
            or new_bottom_y_offset != self.bottom_y_offset
        ):
            print(
                f"Setting {self.bottom_monitor['name']} position to {new_bottom_x_offset}x{new_bottom_y_offset}"
            )
            try:
                subprocess.run(
                    [
                        "xrandr",
                        "--output",
                        self.bottom_monitor["name"],
                        "--pos",
                        f"{new_bottom_x_offset}x{new_bottom_y_offset}",
                    ],
                    check=True,
                )
                # Update the config with the new position
                for monitor in self.config["monitors"]:
                    if monitor["name"] == self.bottom_monitor["name"]:
                        monitor["x_offset"] = new_bottom_x_offset
                        monitor["y_offset"] = (
                            new_bottom_y_offset - self.mouse_height
                        )  # Store the original y_offset
                self.save_config()  # Save the updated config
            except subprocess.CalledProcessError as e:
                print(f"Error setting monitor position: {e}")
                print("Skipping monitor position adjustment.")
        else:
            print(
                f"Monitor {self.bottom_monitor['name']} is already in the correct position."
            )

    def supervise_mouse_position(self, x, y):
        """Print the mouse position and handle jumps when crossing monitor boundaries."""
        if do_print:
            print(f"\r X: {x}, Y: {y}", end="   ", flush=True)

        if (
            abs(y - self.top_height) >= int(self.config["safety_region"])
            or x >= self.top_width
        ):
            return

        if self.do_jump and self.prev_y is not None:
            if (y >= self.top_height and self.prev_y < self.top_height) or (
                y < self.top_height and self.prev_y >= self.top_height
            ):
                direction = "down" if y >= self.top_height else "up"
                new_x = self.handle_jump(x, direction)
                self.mouse_controller.position = (new_x, y)
                print(f"jumped {direction}".upper())

        self.prev_y = y

    def handle_jump(self, old_x, direction):
        top_dpi = self.top_width / self.top_width_cm
        bottom_dpi = self.bottom_width / self.bottom_width_cm
        top_mid = self.top_width // 2
        bottom_x_offset = top_mid - (self.bottom_width // 2)
        bottom_mid = (self.bottom_width // 2) + bottom_x_offset
        offset = old_x - (top_mid if direction == "up" else bottom_mid)
        scaling_factor = (
            bottom_dpi / top_dpi if direction == "down" else top_dpi / bottom_dpi
        )
        new_offset = offset * scaling_factor
        new_x = (bottom_mid if direction == "down" else top_mid) + new_offset
        return new_x

    def setup_and_confirm(self):
        while True:
            self.setup_monitors()
            self.create_config()
            self.set_additional_properties()
            self.get_and_set_monitor_info()
            self.set_monitor_position()
            self.prev_y = None
            self.do_jump = True
            self.mouse_controller = Controller()
            self.set_mousespeed()

            print("Testing setup for 10 seconds...")
            start_time = time.time()
            with Listener(on_move=self.on_move) as listener:
                while time.time() - start_time < 10:
                    time.sleep(0.1)
                    if not listener.running:
                        break

            confirm = input("Is this setup correct? (Y/N): ").upper()
            if confirm == "Y":
                print("Setup confirmed. Saving configuration.")
                self.save_config()
                self.prompt_service_installation()
                break
            else:
                print("Restarting setup process...")
                self.config = None  # Reset config to force new setup

    def on_move(self, x, y):
        self.supervise_mouse_position(x, y)

    def save_config(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        configfile = os.path.join(script_dir, "config.json")
        with open(configfile, "w") as f:
            json.dump(self.config, f, indent=2)
        print(f"Configuration saved to {configfile}")

    def get_mouse_position(self):
        try:
            output = subprocess.check_output(["xdotool", "getmouselocation"]).decode()
            x, y = map(int, output.split()[:2])
            return x, y
        except Exception as e:
            print(f"Error getting mouse position: {e}")
            return 0, 0

    def run(self):
        with Listener(on_move=self.on_move) as listener:
            listener.join()

    def is_config_valid(self):
        if not self.config:
            print("No config found.")
            return False

        config_monitors = self.config.get("monitors", [])
        if len(config_monitors) != len(self.available_monitors):
            print(
                f"Number of monitors mismatch. Config: {len(config_monitors)}, Available: {len(self.available_monitors)}"
            )
            return False

        mouse_height = int(self.config.get("mouse_height", 0))

        for config_monitor in config_monitors:
            matching_monitor = next(
                (
                    m
                    for m in self.available_monitors
                    if m["name"] == config_monitor["name"]
                ),
                None,
            )
            if not matching_monitor:
                print(f"No matching monitor found for {config_monitor['name']}")
                return False

            for key in ["width", "height", "x_offset", "width_mm", "height_mm"]:
                if config_monitor[key] != matching_monitor[key]:
                    print(
                        f"Mismatch in {key} for {config_monitor['name']}. Config: {config_monitor[key]}, Available: {matching_monitor[key]}"
                    )
                    return False

            # Special check for y_offset
            if (
                config_monitor["y_offset"] != matching_monitor["y_offset"]
                and config_monitor["y_offset"]
                != matching_monitor["y_offset"] - mouse_height
            ):
                print(
                    f"Y-offset mismatch for {config_monitor['name']}. Config: {config_monitor['y_offset']}, Available: {matching_monitor['y_offset']}, With mouse height: {matching_monitor['y_offset'] - mouse_height}"
                )
                return False

        print("Configuration is valid.")
        return True

    def apply_config(self):
        self.bottom_monitor = next(
            m
            for m in self.config["monitors"]
            if m["name"] == self.config["bottom_monitor"]
        )
        self.top_monitor = next(
            m
            for m in self.config["monitors"]
            if m["name"] == self.config["top_monitor"]
        )
        self.safety_region = int(self.config["safety_region"])
        self.mousespeed_factor = float(self.config["mousespeed_factor"])
        self.mouse_height = int(self.config["mouse_height"])
        self.set_additional_properties()
        self.get_and_set_monitor_info()
        self.set_monitor_position()
        self.prev_y = None
        self.do_jump = True
        self.mouse_controller = Controller()
        self.set_mousespeed()

    def prompt_service_installation(self):
        install_service = input(
            "Do you want to install this script as a system service? (Y/N): "
        ).upper()
        if install_service == "Y":
            script_dir = os.path.dirname(os.path.abspath(__file__))
            install_script = os.path.join(script_dir, "install_service.py")
            subprocess.run(["python3", install_script])
        else:
            print("Skipping service installation. You can run the script manually.")


if __name__ == "__main__":
    monitor_manager = MonitorManager()
    atexit.register(monitor_manager.cleanup_pid_file)
