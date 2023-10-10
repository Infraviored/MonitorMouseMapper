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
do_print = False
# Initialize mouse controller
mouse_controller = Controller()


# New function
# Changed function
def fetch_available_monitors():
    try:
        command_output = subprocess.check_output(
            ['xrandr', '--query'], text=True)
        monitor_lines = [line.split()[0] for line in command_output.splitlines(
        ) if "connected" in line and not "disconnected" in line]
        return monitor_lines
    except Exception as e:
        print(f"Error: Could not fetch available monitors. Exception: {e}")
        exit(1)


def read_or_create_config(filename="config.json"):
    """Reads the configuration file or creates one if it doesn't exist."""
    # Check if the config file exists
    if os.path.exists(filename):
        with open(filename, "r") as f:
            config = json.load(f)
        # Check if the monitors specified in the config are connected
        available_monitors = fetch_available_monitors()
        saved_monitors = config.get('monitors', [])
        if all(monitor in available_monitors for monitor in saved_monitors):
            print(f"Config read from {filename}: {config}")
            return config
        else:
            print("One or more monitors specified in the config are not connected.")
    else:
        print("No existing config file found.")

    # Fetch all available monitors
    available_monitors = fetch_available_monitors()

    # Show available monitors to the user
    print("Available Monitors:")
    for i, monitor in enumerate(available_monitors):
        print(f"{i + 1}. {monitor}")

    # Initialize config dictionary
    config = {"monitors": []}

    # Loop to select two monitors and their widths
    for monitor_num in ["first", "second"]:
        selected_monitor_index = input(
            f"Select the index of your {monitor_num} monitor from the list above: ")
        selected_monitor_name = available_monitors[int(
            selected_monitor_index) - 1]
        selected_monitor_width = input(
            f"Enter the width in cm of {selected_monitor_name}: ")
        config["monitors"].append(selected_monitor_name)
        config[f"{selected_monitor_name}_WIDTH_CM"] = selected_monitor_width

    # Ask for safety region
    config["safety_region"] = input(
        "Enter the safety region in pixels (default: 200): ") or "200"

    # Save the new config
    with open(filename, "w") as f:
        json.dump(config, f)

    print(f"New config created: {config}")
    return config


def get_monitor_info(monitor):
    """Fetch the monitor details using xrandr and return them."""
    try:
        command_output = subprocess.check_output(
            ['xrandr', '--query'], text=True)
        monitor_line = [line for line in command_output.splitlines(
        ) if monitor in line and "connected" in line][0]
        resolution_info = re.search(
            r'(\d+)x(\d+)\+(\d+)\+(\d+)', monitor_line).groups()
        return tuple(map(int, resolution_info))
    except Exception as e:
        print(
            f"Error: Could not find resolution info for {monitor}. Exception: {e}")
        exit(1)


def set_monitor_position():
    """Set the monitor position using xrandr."""
    NEW_EDP_X_OFFSET = (DP0_WIDTH - EDP_WIDTH) // 2 + DP0_X_OFFSET
    NEW_EDP_Y_OFFSET = DP0_HEIGHT
    subprocess.run(['xrandr', '--output', 'eDP-1-1', '--pos',
                   f"{NEW_EDP_X_OFFSET}x{NEW_EDP_Y_OFFSET}"])


def supervise_mouse_position(x, y):
    """Print the mouse position and handle jumps when crossing monitor boundaries."""
    if do_print:
        print(f"\r X: {x}, Y: {y}", end="   ", flush=True)

    if abs(y - DP0_HEIGHT) >= safety_region:
        return
    global prev_y

    if do_jump and prev_y is not None:
        # Include a delay if within safety_region of the jump
        if (y >= DP0_HEIGHT and prev_y < DP0_HEIGHT) or (y < DP0_HEIGHT and prev_y >= DP0_HEIGHT):
            direction = 'down' if y >= DP0_HEIGHT else 'up'
            new_x = handle_jump(x, direction)
            mouse_controller.position = (new_x, y)

    prev_y = y


def handle_jump(old_x, direction):
    """Calculate the new x-coordinate after a jump between monitors."""
    DP0_DPI = DP0_WIDTH / DP0_WIDTH_CM
    EDP_DPI = EDP_WIDTH / EDP_WIDTH_CM
    DP0_MID = DP0_WIDTH // 2
    EDP_X_OFFSET = DP0_MID - (EDP_WIDTH // 2)
    EDP_MID = (EDP_WIDTH // 2) + EDP_X_OFFSET
    offset = old_x - (DP0_MID if direction == 'up' else EDP_MID)
    scaling_factor = EDP_DPI / DP0_DPI if direction == 'down' else DP0_DPI / EDP_DPI
    new_offset = offset * scaling_factor
    new_x = (EDP_MID if direction == 'down' else DP0_MID) + new_offset
    return new_x


if __name__ == "__main__":
    # Read or create configuration
    config = read_or_create_config()
    EDP_WIDTH_CM = float(config.get("EDP_WIDTH_CM", 34.4))
    DP0_WIDTH_CM = float(config.get("DP0_WIDTH_CM", 62.2))
    safety_region = int(config.get("safety_region", 200))

    do_jump = True
    prev_y = None

    # Fetch monitor information
    DP0_WIDTH, DP0_HEIGHT, DP0_X_OFFSET, DP0_Y_OFFSET = get_monitor_info(
        "DP-0")
    EDP_WIDTH, EDP_HEIGHT, EDP_X_OFFSET, EDP_Y_OFFSET = get_monitor_info(
        "eDP-1-1")

    # Set monitor position
    set_monitor_position()

    # Monitor mouse events with delay to reduce CPU usage
    with Listener(on_move=supervise_mouse_position) as listener:
        listener.join()
