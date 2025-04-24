#!/usr/bin/env python3

"""
Monitor Mouse Mapper - Main Entry Point
---------------------------------------
Maps mouse movements between monitors based on physical coordinates
rather than pixel coordinates, providing more natural transitions.
"""

import json
import os
import signal
import sys
import logging
import time
from pynput.mouse import Controller, Listener
from monitor import Monitor
from physical_mapper import PhysicalMapper


def setup_logging():
    """Set up logging configuration."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, "monitor_mouse_mapper.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(__name__)


def load_config(config_path):
    """Load configuration from JSON file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading config: {e}")
        return None


class MonitorMouseMapper:
    """Main class that coordinates monitor mapping and mouse control."""
    
    def __init__(self):
        """Initialize the monitor mouse mapper."""
        self.logger = setup_logging()
        self.logger.info("Starting MonitorMouseMapper")
        
        # Set up paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.pid_file = os.path.join(self.script_dir, "monitor_manager.pid")
        self.config_file = os.path.join(self.script_dir, "config.json")
        
        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Check for existing instances
        self.startup_pid_check()
        
        # Load configuration
        self.config = load_config(self.config_file)
        if not self.config:
            self.logger.error("Failed to load configuration")
            sys.exit(1)
        
        # Initialize components
        self.mouse_controller = Controller()
        self.mapper = PhysicalMapper(self.config, self.logger)
        
        # Mouse tracking variables
        self.prev_x = None
        self.prev_y = None
        self.do_jump = True
        
        # Set mouse speed if configured
        self.mousespeed_factor = float(self.config.get("mousespeed_factor", 1.0))
        if self.mousespeed_factor != 1.0:
            self.set_mousespeed()
        
        self.logger.info("MonitorMouseMapper initialized successfully")
    
    def cleanup_pid_file(self):
        """Remove PID file on shutdown."""
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
        self.logger.info("Cleaned up PID file and exiting")
    
    def signal_handler(self, signum, frame):
        """Handle termination signals."""
        self.logger.info(f"Received signal {signum}, shutting down")
        self.cleanup_pid_file()
        sys.exit(0)
    
    def startup_pid_check(self):
        """Check for and handle existing instances of the program."""
        if os.path.exists(self.pid_file):
            with open(self.pid_file, "r") as f:
                old_pid = int(f.read())
            try:
                os.kill(old_pid, 0)  # Check if process is running
                self.logger.info(f"An instance is already running (PID {old_pid}). Stopping it.")
                os.kill(old_pid, signal.SIGTERM)
                time.sleep(1)  # Give it time to terminate
            except OSError:
                self.logger.info("No running instance found")
        
        # Write our PID
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))
    
    def set_mousespeed(self):
        """Set mouse speed factor using xinput."""
        try:
            self.logger.info(f"Setting mouse speed factor to {self.mousespeed_factor}")
            import subprocess
            subprocess.run(
                [
                    "xinput",
                    "--set-prop",
                    "pointer:Logitech G502 HERO Gaming Mouse",
                    "libinput Accel Speed",
                    str(self.mousespeed_factor),
                ]
            )
        except Exception as e:
            self.logger.error(f"Failed to set mouse speed: {e}")
    
    def on_move(self, x, y):
        """Handle mouse movement events."""
        print(f"\r X: {x}, Y: {y}", end="   ", flush=True)
        
        if self.do_jump and self.prev_x is not None and self.prev_y is not None:
            # Track position for trajectory calculation
            self.mapper.track_position(x, y)
            
            # Check for monitor border crossing
            new_position = self.mapper.handle_mouse_movement(x, y, self.prev_x, self.prev_y)
            
            if new_position:
                new_x, new_y = new_position
                self.logger.info(f"Jumping from ({x}, {y}) to ({new_x}, {new_y})")
                print(f"\nJUMPED to ({new_x}, {new_y})")
                
                # Move mouse to new position
                self.mouse_controller.position = (new_x, new_y)
                
                # Reset trajectory tracking after jump
                self.mapper.reset_trajectory_tracking()
        
        # Update previous position
        self.prev_x = x
        self.prev_y = y
    
    def run(self):
        """Start the mouse listener and main loop."""
        self.logger.info("Starting mouse listener")
        try:
            with Listener(on_move=self.on_move) as listener:
                listener.join()
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
    
    def __del__(self):
        """Clean up resources when object is destroyed."""
        self.cleanup_pid_file()


if __name__ == "__main__":
    print("Starting MonitorMouseMapper")
    try:
        mapper = MonitorMouseMapper()
        mapper.run()
    except Exception as e:
        print(f"ERROR: An unhandled exception occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
