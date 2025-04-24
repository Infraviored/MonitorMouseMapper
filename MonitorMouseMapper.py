#!/usr/bin/env python3

import re
import subprocess
import sys
import os
import traceback

# Add better error handling for Wayland/X11 issues
print("Starting MonitorMouseMapper.py")
print(f"Python version: {sys.version}")
print(f"DISPLAY: {os.environ.get('DISPLAY')}")
print(f"XAUTHORITY: {os.environ.get('XAUTHORITY')}")

try:
    print("Attempting to import pynput...")
    from pynput.mouse import Controller, Listener
    print("Successfully imported pynput!")
except Exception as e:
    print(f"Error importing pynput: {e}")
    print("Detailed traceback:")
    traceback.print_exc()
    sys.exit(1)

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


# Wrap the entire script in a try-except block
try:
    class MonitorManager:
        def __init__(self):
            print("Initializing MonitorManager...")
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
            self.setup_logging()
            self.pid_file = os.path.join(self.script_dir, "monitor_manager.pid")
            self.config_file = os.path.join(self.script_dir, "config.json")
            self.config_flag_file = os.path.join(self.script_dir, "config_complete.flag")
            self.register_signal_handlers()
            self.startup_pid_check()
            self.load_and_apply_config()

        def setup_logging(self):
            print("Setting up logging...")
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
                self.logger.info("No existing PID file found. Starting a new one.")

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
            
            # Check if configured monitors exist in the current setup
            try:
                available_monitors = [m["name"] for m in self.fetch_available_monitors()]
                
                # Check if top monitor exists
                if self.config["top_monitor"] not in available_monitors:
                    self.logger.error(f"Error: Configured top monitor '{self.config['top_monitor']}' not found in available monitors: {available_monitors}")
                    print(f"\n⚠️ ERROR: Configured top monitor '{self.config['top_monitor']}' not found!")
                    print(f"Available monitors: {', '.join(available_monitors)}")
                    print("Please run the configurator tool to update your settings.")
                    return False
                    
                # Check if bottom monitor exists
                if self.config["bottom_monitor"] not in available_monitors:
                    self.logger.error(f"Error: Configured bottom monitor '{self.config['bottom_monitor']}' not found in available monitors: {available_monitors}")
                    print(f"\n⚠️ ERROR: Configured bottom monitor '{self.config['bottom_monitor']}' not found!")
                    print(f"Available monitors: {', '.join(available_monitors)}")
                    print("Please run the configurator tool to update your settings.")
                    return False
            except Exception as e:
                self.logger.error(f"Error validating monitor configuration: {e}")
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
            edge_mapping_value = self.config.get("edge_mapping", False)
            self.logger.info(f"[APPLY_CONFIG] Assigning 'edge_mapping' with value: {edge_mapping_value} (Type: {type(edge_mapping_value)})")
            self.edge_mapping = edge_mapping_value 
            self.set_additional_properties()
            self.get_and_set_monitor_info()
            self.set_monitor_position()
            self.prev_y = None
            self.do_jump = True
            self.mouse_controller = Controller()
            self.set_mousespeed()

            # Log the applied general settings
            self.logger.info("--- Applied Configuration Settings ---")
            self.logger.info(f"  Top Monitor:    {self.config['top_monitor']}")
            self.logger.info(f"  Bottom Monitor: {self.config['bottom_monitor']}")
            self.logger.info(f"  Safety Region:  {self.safety_region} px")
            self.logger.info(f"  Mouse Speed:    {self.mousespeed_factor}x")
            self.logger.info(f"  Mouse Height:   {self.mouse_height} px")
            self.logger.info(f"  Edge Mapping:   {'Enabled' if self.edge_mapping else 'Disabled'}")
            self.logger.info("------------------------------------")

        def launch_configurator(self):
            self.logger.info("Launching configurator.")
            configurator_path = os.path.join(self.script_dir, "ConfiguratorTool.py")
            try:
                subprocess.Popen(
                    ["x-terminal-emulator", "-e", f"python3 {configurator_path}"]
                )
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to launch configurator: {e}")
                sys.exit(1)

        def wait_for_config(self):
            self.logger.info("Waiting for configuration to complete...")
            while not os.path.exists(self.config_flag_file):
                sleep(1)
            os.remove(self.config_flag_file)
            self.logger.info("Configuration completed.")

        def set_additional_properties(self):
            self.top_width_mm = self.top_monitor["width_mm"]
            self.bottom_width_mm = self.bottom_monitor["width_mm"]

        def get_and_set_monitor_info(self):
            """Retrieves and stores detailed info for the selected top and bottom monitors."""
            try:
                # Ensure top_monitor and bottom_monitor point to the dictionaries within self.config["monitors"]
                self.top_monitor = next(m for m in self.config["monitors"] if m['name'] == self.config["top_monitor"])
                self.bottom_monitor = next(m for m in self.config["monitors"] if m['name'] == self.config["bottom_monitor"])

                self.top_width = int(self.top_monitor["width"])
                self.top_height = int(self.top_monitor["height"])
                self.top_x_offset = int(self.top_monitor["x_offset"])
                self.top_y_offset = int(self.top_monitor["y_offset"])
                self.top_width_mm = float(self.top_monitor.get("width_mm", 0)) # Get physical width, default 0

                self.bottom_width = int(self.bottom_monitor["width"])
                self.bottom_height = int(self.bottom_monitor["height"])
                self.bottom_x_offset = int(self.bottom_monitor["x_offset"])
                self.bottom_y_offset = int(self.bottom_monitor["y_offset"])
                self.bottom_width_mm = float(self.bottom_monitor.get("width_mm", 0)) # Get physical width, default 0

                self.logger.info(f"Top Monitor ({self.top_monitor['name']}): {self.top_width}x{self.top_height}+{self.top_x_offset}+{self.top_y_offset} ({self.top_width_mm}mm wide)")
                self.logger.info(f"Bottom Monitor ({self.bottom_monitor['name']}): {self.bottom_width}x{self.bottom_height}+{self.bottom_x_offset}+{self.bottom_y_offset} ({self.bottom_width_mm}mm wide)")
                self.logger.info(f"Edge Mapping Mode: {'Enabled' if self.edge_mapping else 'Disabled'}")

                if self.top_width_mm <= 0 or self.bottom_width_mm <= 0:
                    self.logger.warning("Physical width (width_mm) not found or invalid for one or both monitors. Physical mapping/overlap calculation may be inaccurate. Ensure config.json is complete.")
                    # Set jump ranges to full monitor width as a fallback? Or leave as (0,0)?
                    # Let's default to full width if physical info is missing, mimicking non-physical behavior
                    self.top_jump_range_px = (self.top_x_offset, self.top_x_offset + self.top_width)
                    self.bottom_jump_range_px = (self.bottom_x_offset, self.bottom_x_offset + self.bottom_width)
                    self.logger.warning(f"Falling back to full width jump zones due to missing physical data.")
                else:
                    # Calculate physical overlap pixel ranges
                    self.calculate_physical_jump_zones()

            except StopIteration:
                self.logger.error(
                    f"Error: Top ('{self.config.get('top_monitor')}') or Bottom ('{self.config.get('bottom_monitor')}') monitor name from config not found in monitor list."
                )

        def calculate_physical_jump_zones(self):
            """Calculates the pixel ranges on each monitor corresponding to the physical overlap,
               assuming physical centers are aligned.
            """
            try:
                top_dpi = self.top_width / self.top_width_mm
                bottom_dpi = self.bottom_width / self.bottom_width_mm

                physically_wider_mm = max(self.top_width_mm, self.bottom_width_mm)
                physically_narrower_mm = min(self.top_width_mm, self.bottom_width_mm)

                # Determine which monitor is physically wider/narrower
                if self.top_width_mm >= self.bottom_width_mm:
                    wider_mon = self.top_monitor
                    wider_dpi = top_dpi
                    wider_offset_px = self.top_x_offset
                    narrower_mon = self.bottom_monitor
                    narrower_dpi = bottom_dpi
                    narrower_offset_px = self.bottom_x_offset
                    narrower_width_px = self.bottom_width
                else:
                    wider_mon = self.bottom_monitor
                    wider_dpi = bottom_dpi
                    wider_offset_px = self.bottom_x_offset
                    narrower_mon = self.top_monitor
                    narrower_dpi = top_dpi
                    narrower_offset_px = self.top_x_offset
                    narrower_width_px = self.top_width

                # Calculate physical positioning (assuming centers aligned)
                wider_center_mm = physically_wider_mm / 2.0
                narrower_center_mm = physically_narrower_mm / 2.0
                narrower_start_offset_rel_wider_mm = wider_center_mm - narrower_center_mm
                narrower_end_offset_rel_wider_mm = wider_center_mm + narrower_center_mm

                # --- Calculate Pixel Range on Wider Monitor --- 
                overlap_start_px_on_wider = wider_offset_px + (narrower_start_offset_rel_wider_mm * wider_dpi)
                overlap_end_px_on_wider = wider_offset_px + (narrower_end_offset_rel_wider_mm * wider_dpi)
                wider_jump_range = (int(round(overlap_start_px_on_wider)), int(round(overlap_end_px_on_wider)))

                # --- Calculate Pixel Range on Narrower Monitor --- 
                # This corresponds to the full width of the narrower monitor
                overlap_start_px_on_narrower = narrower_offset_px
                overlap_end_px_on_narrower = narrower_offset_px + narrower_width_px
                narrower_jump_range = (overlap_start_px_on_narrower, overlap_end_px_on_narrower)

                # Store results based on top/bottom assignment
                if self.top_width_mm >= self.bottom_width_mm:
                    self.top_jump_range_px = wider_jump_range
                    self.bottom_jump_range_px = narrower_jump_range
                else:
                    self.top_jump_range_px = narrower_jump_range
                    self.bottom_jump_range_px = wider_jump_range

                self.logger.info(f"Calculated Physical Jump Zones (Pixel Ranges):")
                self.logger.info(f"  Top Monitor ({self.top_monitor['name']}): {self.top_jump_range_px[0]}px - {self.top_jump_range_px[1]}px")
                self.logger.info(f"  Bottom Monitor ({self.bottom_monitor['name']}): {self.bottom_jump_range_px[0]}px - {self.bottom_jump_range_px[1]}px")

            except ZeroDivisionError:
                self.logger.error("Division by zero during jump zone calculation (width_mm is likely 0). Cannot calculate physical zones.")
                # Fallback to full width
                self.top_jump_range_px = (self.top_x_offset, self.top_x_offset + self.top_width)
                self.bottom_jump_range_px = (self.bottom_x_offset, self.bottom_x_offset + self.bottom_width)
                self.logger.warning(f"Falling back to full width jump zones due to calculation error.")

        def set_monitor_position(self):
            """Applies the x and y positions for all monitors as defined in the config using xrandr."""
            self.logger.info("Applying monitor positions from config...")
            for monitor in self.config.get("monitors", []):
                name = monitor.get("name")
                x_offset = monitor.get("x_offset")
                y_offset = monitor.get("y_offset")

                if name is None or x_offset is None or y_offset is None:
                    self.logger.warning(f"Skipping monitor entry due to missing data: {monitor}")
                    continue

                try:
                    command = [
                        "xrandr",
                        "--output",
                        str(name),
                        "--pos",
                        f"{x_offset}x{y_offset}",
                    ]
                    self.logger.info(f"Running command: {' '.join(command)}")
                    result = subprocess.run(command, check=True, capture_output=True, text=True)
                    self.logger.info(f"Successfully set position for {name} to {x_offset}x{y_offset}.")
                    if result.stdout:
                         self.logger.debug(f"xrandr stdout for {name}: {result.stdout.strip()}")
                    if result.stderr:
                         self.logger.warning(f"xrandr stderr for {name}: {result.stderr.strip()}")
                     
                except FileNotFoundError:
                     self.logger.error("xrandr command not found. Cannot set monitor positions.")
                     # Potentially raise an error or exit if xrandr is essential
                     break # Stop trying if xrandr isn't installed
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Error setting position for {name}: {e}")
                    self.logger.error(f"Command failed: {' '.join(e.cmd)}")
                    self.logger.error(f"Stderr: {e.stderr}")
                except Exception as e:
                     self.logger.error(f"An unexpected error occurred while setting position for {name}: {e}")

            self.logger.info("Finished applying monitor positions.")

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
            """Print the mouse position and handle jumps when crossing monitor boundaries."""
            # Always print X/Y inline
            if do_print:
                print(f"\r X: {x}, Y: {y}", end="   ", flush=True)

            # Only check if we're in the safety region around the border (near y boundary)
            # Important: We no longer check x >= top_width which was preventing jumps from wider monitors
            if abs(y - self.top_height) >= int(self.config["safety_region"]):
                return

            if self.do_jump and self.prev_y is not None:
                # Check if we're crossing the boundary between monitors
                crossing_up = (y < self.top_height and self.prev_y >= self.top_height)
                crossing_down = (y >= self.top_height and self.prev_y < self.top_height)
                
                if crossing_up or crossing_down:
                    direction = "down" if crossing_down else "up"
                    # Log details about the crossing
                    print(f"\n[DEBUG] Crossing border! Direction: {direction}, x: {x}, prev_y: {self.prev_y}, y: {y}")
                    
                    # Calculate the new X position for the jump
                    new_x = self.handle_jump(x, direction, debug=True)
                    
                    # Only move mouse if handle_jump returned a valid coordinate (not None)
                    if new_x is not None:
                        print(f"JUMPED {direction.upper()}: to new x position {new_x}")
                        self.mouse_controller.position = (new_x, y)
                    else:
                        print(f"NO JUMP: handle_jump returned None")
                        new_x = x  # Keep original position
            else:
                new_x = x

            self.prev_y = y

        def handle_jump(self, old_x_abs, direction, debug=False):
            """Calculates the new X-coordinate when crossing monitor boundaries,
            aiming to preserve the physical horizontal position.

            Args:
                old_x_abs: The absolute X-coordinate where the cursor crossed.
                direction: 'up' (bottom to top) or 'down' (top to bottom).
                debug: If True, print detailed calculation steps.

            Returns:
                The calculated new absolute X-coordinate on the destination monitor,
                or None if the jump should not occur (due to physical non-overlap).
            """

            # --- 1. Basic Sanity Checks and DPI Calculation ---
            if self.top_width_mm <= 0 or self.bottom_width_mm <= 0:
                if debug:
                    print("[DEBUG] Cannot perform physical jump: Monitor physical width (width_mm) is missing or invalid.")
                # Fallback to previous simple relative pixel mapping? Or just return old_x?
                # For now, let's prevent the jump entirely if physical info is bad.
                return None # Indicate no jump

            try:
                top_dpi = self.top_width / self.top_width_mm
                bottom_dpi = self.bottom_width / self.bottom_width_mm
            except ZeroDivisionError:
                if debug:
                     print("[DEBUG] Cannot perform physical jump: Division by zero calculating DPI (width_mm is likely 0).")
                return None # Indicate no jump

            # --- 2. Identify Source and Destination Monitors --- 
            if direction == "down": # Top -> Bottom
                source_name = self.top_monitor['name']
                source_width_px = self.top_width
                source_width_mm = self.top_width_mm
                source_x_offset = self.top_x_offset
                source_dpi = top_dpi

                dest_name = self.bottom_monitor['name']
                dest_width_px = self.bottom_width
                dest_width_mm = self.bottom_width_mm
                dest_x_offset = self.bottom_x_offset
                dest_dpi = bottom_dpi
            else: # Bottom -> Top ("up")
                source_name = self.bottom_monitor['name']
                source_width_px = self.bottom_width
                source_width_mm = self.bottom_width_mm
                source_x_offset = self.bottom_x_offset
                source_dpi = bottom_dpi

                dest_name = self.top_monitor['name']
                dest_width_px = self.top_width
                dest_width_mm = self.top_width_mm
                dest_x_offset = self.top_x_offset
                dest_dpi = top_dpi

            if debug:
                print(f"[DEBUG] ---- handle_jump ({direction}) ----")
                print(f"[DEBUG] Cursor crossed at absolute X: {old_x_abs}")
                print(f"[DEBUG] Source: {source_name} ({source_width_px}px, {source_width_mm:.1f}mm, offset={source_x_offset}, dpi={source_dpi:.2f})")
                print(f"[DEBUG] Dest:   {dest_name} ({dest_width_px}px, {dest_width_mm:.1f}mm, offset={dest_x_offset}, dpi={dest_dpi:.2f})")

            # --- 3. Calculate Physical Position on Source Monitor --- 
            # Cursor X relative to the source monitor's left edge (in pixels)
            old_x_rel_px = old_x_abs - source_x_offset
            
            # Check if cursor is within bounds of the source monitor
            if old_x_rel_px < 0 or old_x_rel_px > source_width_px:
                if debug:
                    print(f"[DEBUG] Warning: Cursor X position ({old_x_rel_px}) is outside source monitor bounds (0 to {source_width_px}).")
                    print(f"[DEBUG] Will continue calculation but results may be unexpected.")
            
            # Physical distance from the source monitor's physical left edge (in mm)
            source_physical_pos_mm = old_x_rel_px / source_dpi

            if debug:
                 print(f"[DEBUG] Cursor relative X on source: {old_x_rel_px:.1f} px")
                 print(f"[DEBUG] Cursor physical position from source left edge: {source_physical_pos_mm:.2f} mm")

            # --- 4. Overlap Check & Target Physical Position Calculation ---
            physically_wider_mon_mm = max(self.top_width_mm, self.bottom_width_mm)
            physically_narrower_mon_mm = min(self.top_width_mm, self.bottom_width_mm)

            # Physical centers relative to their own left edges
            wider_center_mm = physically_wider_mon_mm / 2.0
            narrower_center_mm = physically_narrower_mon_mm / 2.0
            
            # Physical start offset of the narrower monitor relative to the wider monitor's start edge
            # (Assumes physical centers are aligned)
            narrower_start_offset_rel_wider_mm = wider_center_mm - narrower_center_mm
            narrower_end_offset_rel_wider_mm = wider_center_mm + narrower_center_mm

            target_physical_pos_rel_dest_mm = None

            # Case 1: Moving from Physically Wider -> Narrower
            if source_width_mm > dest_width_mm:
                if debug:
                    print(f"[DEBUG] Moving Wider -> Narrower. Checking physical overlap.")
                    print(f"[DEBUG] Narrower physical span relative to wider start: [{narrower_start_offset_rel_wider_mm:.2f} mm, {narrower_end_offset_rel_wider_mm:.2f} mm]")

                # Check if the cursor's physical position on the wider monitor falls within the narrower monitor's span
                is_within_overlap = (narrower_start_offset_rel_wider_mm <= source_physical_pos_mm <= narrower_end_offset_rel_wider_mm)

                if is_within_overlap:
                    # Calculate target physical position relative to the *narrower* monitor's start edge
                    target_physical_pos_rel_dest_mm = source_physical_pos_mm - narrower_start_offset_rel_wider_mm
                    if debug:
                        print(f"[DEBUG] Cursor is within physical overlap.")
                else:
                    # Cursor is OUTSIDE the physical overlap
                    if self.edge_mapping:
                        if debug:
                            print(f"[DEBUG] Cursor physical position ({source_physical_pos_mm:.2f} mm) is outside overlap. Applying EDGE MAPPING.")
                        # Snap to the nearest edge of the destination (narrower) monitor
                        if source_physical_pos_mm < narrower_start_offset_rel_wider_mm:
                             # Snap to left edge
                             target_physical_pos_rel_dest_mm = 0.0
                             if debug: print(f"[DEBUG] Snapping to LEFT edge (0.0 mm) of destination.")
                        else: # source_physical_pos_mm > narrower_end_offset_rel_wider_mm
                             # Snap to right edge
                             target_physical_pos_rel_dest_mm = dest_width_mm
                             if debug: print(f"[DEBUG] Snapping to RIGHT edge ({dest_width_mm:.2f} mm) of destination.")
                    else:
                        # Edge mapping is off, no jump
                        if debug:
                            print(f"[DEBUG] Cursor physical position ({source_physical_pos_mm:.2f} mm) is outside the narrower monitor's physical span. Edge mapping OFF. NO JUMP.")
                        return None # Indicate no jump should occur

            # Case 2: Moving from Physically Narrower -> Wider
            elif source_width_mm < dest_width_mm: 
                 if debug:
                    print(f"[DEBUG] Moving Narrower -> Wider. Jump always possible (assuming vertical alignment).")
                 # The source physical position is relative to the narrower monitor's start.
                 # Calculate the target physical position relative to the *wider* monitor's start edge.
                 target_physical_pos_rel_dest_mm = source_physical_pos_mm + narrower_start_offset_rel_wider_mm
                 
            # Case 3: Monitors have same physical width (unlikely with mm precision, but handle it)
            else:
                 if debug:
                     print(f"[DEBUG] Monitors have same physical width. Direct mapping.")
                 target_physical_pos_rel_dest_mm = source_physical_pos_mm

            if target_physical_pos_rel_dest_mm is None: # Should not happen if logic above is correct, but safety check
                 if debug:
                     print("[DEBUG] Error: Target physical position calculation failed unexpectedly.")
                 return None

            if debug:
                 print(f"[DEBUG] Target physical position relative to destination left edge: {target_physical_pos_rel_dest_mm:.2f} mm")

            # --- 5. Convert Target Physical Position to Destination Pixels --- 
            # Target X relative to the destination monitor's left edge (in pixels)
            new_x_rel_px = target_physical_pos_rel_dest_mm * dest_dpi
            
            # Ensure result is within destination monitor's bounds
            new_x_rel_px = max(0, min(new_x_rel_px, dest_width_px))
            
            # Target absolute X coordinate
            new_x_abs = dest_x_offset + new_x_rel_px

            if debug:
                 print(f"[DEBUG] Target relative X on destination: {new_x_rel_px:.1f} px")
                 print(f"[DEBUG] Calculated new absolute X: {new_x_abs:.1f}")
                 print(f"[DEBUG] ---- End handle_jump ----")

            # Return the integer coordinate
            return int(round(new_x_abs))

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

        def load_and_apply_config(self):
            """Loads configuration, validates it, and applies settings."""
            self.available_monitors = self.fetch_available_monitors()
            self.config = self.read_config()
            if self.config:
                # Log edge_mapping right after reading
                self.logger.info(f"[LOAD_CONFIG] Value of 'edge_mapping' after read_config: {self.config.get('edge_mapping', 'Not Found')}")
                if not self.is_config_valid():
                    self.logger.warning(
                        "Current config is invalid. Launching configurator."
                    )
                    self.launch_configurator()
                    self.wait_for_config()
                    self.config = self.read_config()  # Re-read after configuration
                    self.logger.info(f"[LOAD_CONFIG] Value of 'edge_mapping' after re-read: {self.config.get('edge_mapping', 'Not Found')}")

                # Log edge_mapping just before applying
                self.logger.info(f"[LOAD_CONFIG] Value of 'edge_mapping' before apply_config: {self.config.get('edge_mapping', 'Not Found')}")
                self.apply_config()
                self.logger.info("Configuration loaded and applied successfully.")
            else:
                self.logger.error(
                    "No configuration found. Please run the configurator tool to create one."
                )
            self.run()

        def __del__(self):
            self.cleanup_pid_file()

    if __name__ == "__main__":
        print("Starting main...")
        monitor_manager = MonitorManager()
        print("MonitorManager initialized, entering the main listener loop...")
        with Listener(on_move=monitor_manager.supervise_mouse_position) as listener:
            listener.join()

except Exception as e:
    print(f"ERROR: An unhandled exception occurred: {e}")
    print("Detailed traceback:")
    traceback.print_exc()
    sys.exit(1)
