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
import logging

global sleep_duration
sleep_duration = 0.01

global do_print
do_print = True


class MonitorManager:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.setup_logging()
        self.pid_file = os.path.join(self.script_dir, "monitor_manager.pid")
        self.config_file = os.path.join(self.script_dir, "config.json")
        self.register_signal_handlers()
        self.startup_pid_check()
        self.available_monitors = self.fetch_available_monitors()
        self.config = self.read_config()
        if self.is_config_valid():
            self.logger.info("Using existing configuration.")
            self.apply_config()
        else:
            self.logger.info("Current setup is not configured. Launching configurator.")
            self.launch_configurator()
        self.run()

    def setup_logging(self):
        log_file = os.path.join(self.script_dir, "monitor_mouse_mapper.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def register_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        self.cleanup_pid_file()
        sys.exit(0)

    def cleanup_pid_file(self):
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
        self.logger.info("Cleaned up PID file and exiting.")

    def startup_pid_check(self):
        if os.path.exists(self.pid_file):
            with open(self.pid_file, "r") as f:
                old_pid = int(f.read())
            try:
                os.kill(old_pid, 0)  # Check if process is running
                self.logger.info(
                    f"An instance of the script is already running with PID {old_pid}. Stopping it."
                )
                os.kill(old_pid, signal.SIGTERM)  # Terminate the old process
                sleep(1)  # Give it some time to terminate
                self.logger.info("Terminated the old instance. Starting a new one.")
            except OSError:
                self.logger.info("No running instance found. Starting a new one.")
        else:
            self.logger.info("No existing PID file found. Starting a new instance.")

        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

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
            self.logger.error(
                f"Error: Could not fetch available monitors. Exception: {e}"
            )
            sys.exit(1)

    def read_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                self.logger.info(f"Config read from {self.config_file}: {config}")
                return config
            except json.JSONDecodeError:
                self.logger.error("Error reading config file. Creating a new one.")
        return None

    def is_config_valid(self):
        if not self.config:
            return False
        # Add more validation checks here if needed
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

    def launch_configurator(self):
        self.logger.info("Launching configurator.")
        configurator_path = os.path.join(self.script_dir, "ConfiguratorTool.py")
        try:
            subprocess.run(
                ["x-terminal-emulator", "-e", f"python3 {configurator_path}"],
                check=True,
            )
            self.logger.info("Configurator completed. Restarting service.")
            os.execv(sys.executable, ["python3"] + sys.argv)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to launch configurator: {e}")
            sys.exit(1)

    def set_additional_properties(self):
        # Implement any additional property setting logic here
        pass

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

    def get_monitor_info(self, monitor_name):
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
            self.logger.error(
                f"Error: Could not find resolution info for {monitor_name}. Exception: {e}"
            )
            sys.exit(1)

    def set_monitor_position(self):
        new_bottom_y_offset = self.top_monitor["height"] + self.mouse_height
        if self.bottom_monitor["y_offset"] != new_bottom_y_offset:
            subprocess.run(
                [
                    "xrandr",
                    "--output",
                    self.bottom_monitor["name"],
                    "--pos",
                    f"{self.bottom_monitor['x_offset']}x{new_bottom_y_offset}",
                ]
            )
            self.bottom_y_offset = new_bottom_y_offset
            self.bottom_monitor["y_offset"] = new_bottom_y_offset
            self.save_config()

    def set_mousespeed(self):
        if self.mousespeed_factor != 1.0:
            self.logger.info(f"Setting mousespeed factor to {self.mousespeed_factor}")
            subprocess.run(
                [
                    "xinput",
                    "--set-prop",
                    "pointer:Logitech G502 HERO Gaming Mouse",
                    "libinput Accel Speed",
                    str(self.mousespeed_factor),
                ]
            )

    def supervise_mouse_position(self, x, y):
        if do_print:
            print(f"\r X: {x}, Y: {y}", end="   ", flush=True)

        if self.bottom_y_offset <= y < self.bottom_y_offset + self.safety_region:
            if self.prev_y is not None and self.prev_y < self.bottom_y_offset:
                new_y = self.top_y_offset + self.top_height - self.safety_region
                self.mouse_controller.position = (x, new_y)
        elif (
            self.top_y_offset + self.top_height - self.safety_region
            <= y
            < self.top_y_offset + self.top_height
        ):
            if (
                self.prev_y is not None
                and self.prev_y >= self.top_y_offset + self.top_height
            ):
                new_y = self.bottom_y_offset + self.safety_region
                self.mouse_controller.position = (x, new_y)
        self.prev_y = y

    def on_move(self, x, y):
        self.supervise_mouse_position(x, y)

    def run(self):
        self.prev_y = None
        try:
            with Listener(on_move=self.on_move) as listener:
                listener.join()
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)
        self.logger.info(f"Configuration saved to {self.config_file}")


if __name__ == "__main__":
    monitor_manager = MonitorManager()
