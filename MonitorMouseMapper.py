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
        self.config = None
        self.read_or_create_config()
        self.pick_monitors()
        self.set_additional_properties()
        self.get_and_set_monitor_info()
        self.set_monitor_position()
        self.prev_y = None
        self.do_jump = True
        self.mouse_controller = Controller()
        self.set_120_mousespeed()
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
                print(f"An instance of the script is already running with PID {old_pid}. Stopping it.")
                os.kill(old_pid, signal.SIGTERM)  # Terminate the old process
                sleep(1)  # Give it some time to terminate
                # Since there was a running instance, we exit the new instance after killing the old one
                print("Terminated the old instance. Exiting the new instance to prevent duplicates.")
                exit()
            except OSError:
                print("No running instance found. Starting a new one.")
        else:
            print("No existing PID file found. Starting a new instance.")
        
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))


    def set_120_mousespeed(self):
        #xinput --set-prop 35 217 1.2 0 0 0 1.2 0 0 0 1
        subprocess.run(['xinput', '--set-prop', '35', '217', '1.2', '0', '0', '0', '1.2', '0', '0', '0', '1'])

    def pick_monitors(self):
        available_monitors = self.fetch_available_monitors()
        self.bottom_monitor = next(
            (monitor for monitor in self.config['bottom_monitors'] if monitor['name'] in available_monitors), None)
        self.top_monitor = next(
            (monitor for monitor in self.config['top_monitors'] if monitor['name'] in available_monitors), None)

        if self.bottom_monitor is None or self.top_monitor is None:
            print("Error: No suitable monitors found.")
            exit(1)

    def fetch_available_monitors(self):
        try:
            command_output = subprocess.check_output(
                ['xrandr', '--query'], text=True)
            monitor_lines = [line.split()[0] for line in command_output.splitlines(
            ) if "connected" in line and not "disconnected" in line]
            return monitor_lines
        except Exception as e:
            print(f"Error: Could not fetch available monitors. Exception: {e}")

            exit(1)

    def set_additional_properties(self):
        self.bottom_width_cm = float(self.bottom_monitor.get('width_cm', 34.4))
        self.top_width_cm = float(self.top_monitor.get('width_cm', 62.2))
        self.safety_region = int(self.config.get("safety_region", 200))

    def get_and_set_monitor_info(self):
        self.bottom_width, self.bottom_height, self.bottom_x_offset, self.bottom_y_offset = self.get_monitor_info(
            self.bottom_monitor['name'])
        self.top_width, self.top_height, self.top_x_offset, self.top_y_offset = self.get_monitor_info(
            self.top_monitor['name'])

    # Changed function
    def assign_available_monitors(self):
        available_monitors = self.fetch_available_monitors()
        self.bottom_monitor = next(
            (monitor for monitor in self.config['bottom_monitors'] if monitor['name'] in available_monitors), None)
        self.top_monitor = next(
            (monitor for monitor in self.config['top_monitors'] if monitor['name'] in available_monitors), None)

    def read_or_create_config(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        configfile = os.path.join(script_dir, "config.json")
        config_changed = False

        def is_config_complete(config):
            if not config.get('bottom_monitors') or not config.get('top_monitors'):
                return False
            for monitor in config['bottom_monitors']:
                if 'width_cm' not in monitor or 'mouse_height_px' not in monitor:
                    return False
            for monitor in config['top_monitors']:
                if 'width_cm' not in monitor:
                    return False
            if 'safety_region' not in config:
                return False
            return True

        available_monitors = self.fetch_available_monitors()
        available_bottom_monitor = None
        available_top_monitor = None

        if os.path.exists(configfile):
            with open(configfile, "r") as f:
                self.config = json.load(f)

            # Check for available bottom and top monitors
            available_bottom_monitor = next(
                (monitor for monitor in self.config.get('bottom_monitors', []) if monitor['name'] in available_monitors), None)
            available_top_monitor = next(
                (monitor for monitor in self.config.get('top_monitors', []) if monitor['name'] in available_monitors), None)

            if available_bottom_monitor:
                print("Configured Bottom monitor found.")
            else:
                print("No configured bottom monitor found.")

            if available_top_monitor:
                print("Configured Top monitor found.")
            else:
                print("No configured top monitor found.")

            if is_config_complete(self.config) and available_bottom_monitor and available_top_monitor:
                print(f"Config read from {configfile}: {self.config}")
                self.bottom_monitor = available_bottom_monitor
                self.top_monitor = available_top_monitor
                self.mouse_height = int(available_bottom_monitor.get('mouse_height_px', 0))
                return
            else:
                print("Config file is incomplete. Starting remaining configuration...")

        else:
            print("No existing config file found. Creating new config...")
            self.config = {'bottom_monitors': [], 'top_monitors': []}
            config_changed = True

        print("Available Monitors:")
        for i, monitor in enumerate(available_monitors):
            print(f"{i + 1}. {monitor}")

        if not available_bottom_monitor:
            bottom_monitor_index = input("Select the index of your bottom monitor from the list above: ")
            selected_bottom_monitor = {
                'name': available_monitors[int(bottom_monitor_index) - 1],
                'width_cm': input(f"Enter the width in cm of {available_monitors[int(bottom_monitor_index) - 1]}: "),
                'mouse_height_px': input(f"Enter mouse height in pixels for {available_monitors[int(bottom_monitor_index) - 1]} (default: 30): ") or "30"
            }
            self.config["bottom_monitors"].append(selected_bottom_monitor)
            config_changed = True

        if not available_top_monitor:
            top_monitor_index = input("Select the index of your top monitor from the list above: ")
            selected_top_monitor = {
                'name': available_monitors[int(top_monitor_index) - 1],
                'width_cm': input(f"Enter the width in cm of {available_monitors[int(top_monitor_index) - 1]}: ")
            }
            self.config["top_monitors"].append(selected_top_monitor)
            config_changed = True

        if "safety_region" not in self.config:
            self.config["safety_region"] = input("Enter the safety region in pixels (default: 200): ") or "200"

        if config_changed:
            with open(configfile, "w") as f:
                json.dump(self.config, f)
            print(f"New config created: {self.config}")

        self.bottom_monitor = next(
            (monitor for monitor in self.config['bottom_monitors'] if monitor['name'] in available_monitors), None)
        self.top_monitor = next(
            (monitor for monitor in self.config['top_monitors'] if monitor['name'] in available_monitors), None)
        self.mouse_height = int(self.bottom_monitor.get('mouse_height_px', 0))

    def get_monitor_info(self, monitor_name):
        """Fetch the monitor details using xrandr and return them."""
        try:
            command_output = subprocess.check_output(['xrandr', '--query'], text=True)
            monitor_line = [line for line in command_output.splitlines() if monitor_name in line and "connected" in line][0]
            resolution_info = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', monitor_line).groups()
            return tuple(map(int, resolution_info))
        except Exception as e:
            print(f"Error: Could not find resolution info for {monitor_name}. Exception: {e}")
            exit(1)

    def set_monitor_position(self):
        """Set the monitor position using xrandr."""
        new_bottom_x_offset = (self.top_width - self.bottom_width) // 2 + self.top_x_offset
        new_bottom_y_offset = self.top_height + self.mouse_height
        print(f"Setting {self.bottom_monitor['name']} position to {new_bottom_x_offset}x{new_bottom_y_offset}")
        subprocess.run(['xrandr', '--output', self.bottom_monitor['name'], '--pos', f"{new_bottom_x_offset}x{new_bottom_y_offset}"])


    def supervise_mouse_position(self, x, y):
        """Print the mouse position and handle jumps when crossing monitor boundaries."""
        if do_print:
            print(f"\r X: {x}, Y: {y}", end="   ", flush=True)

        if abs(y - self.top_height) >= int(self.config["safety_region"]) or x >= self.top_width:
            return

        if self.do_jump and self.prev_y is not None:
            if (y >= self.top_height and self.prev_y < self.top_height) or (y < self.top_height and self.prev_y >= self.top_height):
                direction = 'down' if y >= self.top_height else 'up'
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
    atexit.register(monitor_manager.cleanup_pid_file)
