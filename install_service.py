#!/usr/bin/env python3

import os
import subprocess
import sys
import glob
import re
import argparse


def is_service_installed():
    """Check if the service is already installed"""
    service_path = os.path.expanduser("~/.config/systemd/user/monitor-mouse-mapper.service")
    return os.path.exists(service_path)


def is_service_running():
    """Check if the service is currently running"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "monitor-mouse-mapper.service"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip() == "active"
    except:
        return False


def create_desktop_shortcut(script_dir, python_venv):
    """Create a desktop shortcut for the configurator tool"""
    # Create desktop shortcut
    desktop_dir = os.path.expanduser("~/Desktop")
    desktop_file_path = os.path.join(desktop_dir, "MonitorMouseMapper.desktop")
    
    # Also create an entry in the applications directory
    applications_dir = os.path.expanduser("~/.local/share/applications")
    applications_file_path = os.path.join(applications_dir, "MonitorMouseMapper.desktop")
    
    configurator_path = os.path.join(script_dir, "ConfiguratorTool.py")
    icon_path = os.path.join(script_dir, "images/icon_hills.png")
    
    # Check if files already exist
    if os.path.exists(desktop_file_path):
        print(f"Desktop shortcut already exists at {desktop_file_path}")
    if os.path.exists(applications_file_path):
        print(f"Application entry already exists at {applications_file_path}")
        
    # If both already exist, just return
    if os.path.exists(desktop_file_path) and os.path.exists(applications_file_path):
        return
    
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=MonitorMouseMapper
Comment=Configure monitor mouse mapping
Exec=x-terminal-emulator -e {python_venv} {configurator_path}
Icon={icon_path}
Terminal=false
Categories=Utility;
"""
    
    # Create in Desktop directory if it doesn't exist
    if not os.path.exists(desktop_file_path):
        with open(desktop_file_path, "w") as f:
            f.write(desktop_content)
        
        # Make the desktop file executable
        os.chmod(desktop_file_path, 0o755)
        print(f"Desktop shortcut created at {desktop_file_path}")
    
    # Create in applications directory if it doesn't exist
    if not os.path.exists(applications_file_path):
        os.makedirs(applications_dir, exist_ok=True)
        with open(applications_file_path, "w") as f:
            f.write(desktop_content)
        
        # Make the applications file executable
        os.chmod(applications_file_path, 0o755)
        print(f"Application entry created at {applications_file_path}")
    
    # Update desktop database to make the shortcut immediately visible
    try:
        subprocess.run(["update-desktop-database", applications_dir], check=False)
    except Exception:
        pass  # Non-critical if this fails


def check_display_server():
    try:
        session_type = os.environ.get('XDG_SESSION_TYPE', '')
        if session_type.lower() == 'wayland':
            print("\n⚠️ WARNING: You are running a Wayland session!")
            print("Monitor Mouse Mapper is designed for X11 and may not work correctly on Wayland.")
            print("For best results, please log out and select 'Ubuntu on Xorg' at the login screen.")
            response = input("Do you want to continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Installation aborted.")
                sys.exit(1)
    except Exception as e:
        print(f"Could not determine display server type: {e}")
        print("Continuing with installation...")


def validate_configuration():
    """Validate that the configured monitors match available monitors"""
    try:
        import json
        import re
        import subprocess
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, "config.json")
        
        # Check if config file exists
        if not os.path.exists(config_file):
            print("No configuration file found. Will be created during first run.")
            return True
            
        # Read current configuration
        with open(config_file, 'r') as f:
            config = json.load(f)
            
        # Get currently connected monitors using xrandr
        xrandr_output = subprocess.check_output(["xrandr", "--query"], text=True)
        connected_monitors = []
        pattern = r"(\S+) connected"
        for line in xrandr_output.splitlines():
            match = re.search(pattern, line)
            if match:
                connected_monitors.append(match.group(1))
                
        # Check if configured monitors exist
        top_monitor = config.get('top_monitor')
        bottom_monitor = config.get('bottom_monitor')
        
        if top_monitor and top_monitor not in connected_monitors:
            print(f"\n⚠️ WARNING: Configured top monitor '{top_monitor}' is not currently connected!")
            print(f"Connected monitors: {', '.join(connected_monitors)}")
            print("You'll need to run the configurator tool after installation.")
            return False
            
        if bottom_monitor and bottom_monitor not in connected_monitors:
            print(f"\n⚠️ WARNING: Configured bottom monitor '{bottom_monitor}' is not currently connected!")
            print(f"Connected monitors: {', '.join(connected_monitors)}")
            print("You'll need to run the configurator tool after installation.")
            return False
            
        print("✅ Configuration validated: Configured monitors match connected monitors.")
        return True
    except Exception as e:
        print(f"Error validating configuration: {e}")
        return True  # Continue installation despite validation error


def uninstall_service():
    """Uninstall the service and remove desktop shortcuts"""
    try:
        print("Uninstalling Monitor Mouse Mapper service...")
        
        # Stop and disable the service if it exists
        if is_service_installed():
            subprocess.run(["systemctl", "--user", "stop", "monitor-mouse-mapper.service"], check=False)
            subprocess.run(["systemctl", "--user", "disable", "monitor-mouse-mapper.service"], check=False)
            
            # Remove service file
            service_file = os.path.expanduser("~/.config/systemd/user/monitor-mouse-mapper.service")
            if os.path.exists(service_file):
                os.remove(service_file)
                print("Removed service file.")
                
            # Reload daemon
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        else:
            print("Service is not installed, nothing to remove.")
        
        # Remove desktop shortcuts
        desktop_file = os.path.expanduser("~/Desktop/MonitorMouseMapper.desktop")
        if os.path.exists(desktop_file):
            os.remove(desktop_file)
            print(f"Removed desktop shortcut: {desktop_file}")
            
        # Remove application entry
        app_file = os.path.expanduser("~/.local/share/applications/MonitorMouseMapper.desktop")
        if os.path.exists(app_file):
            os.remove(app_file)
            print(f"Removed application entry: {app_file}")
            
        # Note about other files
        print("\nNote: The program files in the current directory have not been removed.")
        print("You can manually delete them if you want to completely remove the program.")
        
        print("\nUninstallation complete.")
        
    except Exception as e:
        print(f"Error during uninstallation: {e}")
        return False
    
    return True


def install_service():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    monitor_mapper_path = os.path.join(script_dir, "MonitorMouseMapper.py")
    venv_dir = os.path.join(script_dir, "venv")
    python_venv = os.path.join(venv_dir, "bin", "python")

    # Check if the service is already installed
    already_installed = is_service_installed()
    if already_installed:
        is_running = is_service_running()
        print(f"Monitor Mouse Mapper service is already installed and {'running' if is_running else 'not running'}.")
        action = input("What would you like to do? (reinstall/uninstall/exit): ").lower()
        
        if action == "uninstall":
            if uninstall_service():
                return
        elif action == "exit":
            print("Exiting without changes.")
            return
        elif action != "reinstall":
            print("Invalid option. Proceeding with reinstallation.")
        
        # If reinstalling, first stop and disable the service
        subprocess.run(["systemctl", "--user", "stop", "monitor-mouse-mapper.service"], check=False)
        subprocess.run(["systemctl", "--user", "disable", "monitor-mouse-mapper.service"], check=False)

    # Check if the MonitorMouseMapper.py file exists
    if not os.path.exists(monitor_mapper_path):
        print(f"Error: {monitor_mapper_path} does not exist.")
        return

    # Create virtual environment if it doesn't exist
    if not os.path.exists(venv_dir):
        print("Creating virtual environment...")
        try:
            # Check if python3-venv is installed
            result = subprocess.run(
                ["dpkg", "-l", "python3-full"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            if "ii" not in result.stdout.decode():
                print("Installing python3-full package...")
                subprocess.run(["sudo", "apt", "install", "-y", "python3-full"], check=True)
            
            # Create virtual environment
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
            
            # Install required packages in the virtual environment
            subprocess.run(
                [python_venv, "-m", "pip", "install", "pynput"], check=True
            )
            print("Virtual environment created and packages installed.")
        except subprocess.CalledProcessError as e:
            print(f"Error setting up virtual environment: {e}")
            return
    
    # Get current DISPLAY value (no need for XAUTHORITY in X11)
    display = os.environ.get('DISPLAY', ':0')
    
    # Check the session type
    session_type = os.environ.get('XDG_SESSION_TYPE', 'unknown')
    print(f"Detected session type: {session_type}")
    
    service_content = f"""[Unit]
Description=Monitor Mouse Mapper Service
After=graphical-session.target
PartOf=graphical-session.target
Requires=graphical-session.target

[Service]
Type=simple
ExecStart={python_venv} -u {monitor_mapper_path}
Restart=on-failure
RestartSec=5
Environment=DISPLAY={display}
StandardOutput=journal
StandardError=journal
WorkingDirectory={script_dir}

[Install]
WantedBy=graphical-session.target
"""

    user_service_dir = os.path.expanduser("~/.config/systemd/user")
    service_file = os.path.join(user_service_dir, "monitor-mouse-mapper.service")

    try:
        # Create user service directory if it doesn't exist
        os.makedirs(user_service_dir, exist_ok=True)

        # Write service file
        with open(service_file, "w") as f:
            f.write(service_content)

        # Reload systemd user daemon
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)

        # Enable and start the service
        subprocess.run(
            ["systemctl", "--user", "enable", "monitor-mouse-mapper.service"],
            check=True,
        )
        
        # Ask if user wants to start the service now
        start_now = input("Would you like to start the service now? (y/n): ").lower()
        if start_now == 'y' or start_now == 'yes':
            subprocess.run(
                ["systemctl", "--user", "start", "monitor-mouse-mapper.service"], check=True
            )
            print("Service started. If it fails, try logging out and back in.")
            print("You can check its status with: systemctl --user status monitor-mouse-mapper.service")
        else:
            print("Service installed but not started. You can start it manually with:")
            print("systemctl --user start monitor-mouse-mapper.service")
        
        # Ask if user wants to create a desktop shortcut
        create_shortcut = input("Would you like to create a desktop shortcut? (y/n): ").lower()
        if create_shortcut == 'y' or create_shortcut == 'yes':
            create_desktop_shortcut(script_dir, python_venv)
        else:
            # Always create the application entry regardless
            applications_dir = os.path.expanduser("~/.local/share/applications")
            applications_file_path = os.path.join(applications_dir, "MonitorMouseMapper.desktop")
            if not os.path.exists(applications_file_path):
                print("Creating application entry for easier access...")
                create_desktop_shortcut(script_dir, python_venv)

        # Validate configuration before finishing
        config_valid = validate_configuration()
        if not config_valid:
            print("\nWould you like to run the configurator now to update your monitor configuration? (y/n): ", end="")
            run_config = input().lower()
            if run_config == 'y' or run_config == 'yes':
                configurator_path = os.path.join(script_dir, "ConfiguratorTool.py")
                subprocess.run([python_venv, configurator_path])
                print("Configuration updated. Service will use the new settings.")
            else:
                print("Please run the configurator manually if you experience issues with the service.")

        print("Installation complete.")
        print("\nIf you have issues with the service not starting correctly, you can:")
        print("1. Check service status: systemctl --user status monitor-mouse-mapper.service")
        print("2. View service logs: journalctl --user -u monitor-mouse-mapper.service -n 50")
        print("3. Run the configurator: python3 ConfiguratorTool.py")

    except subprocess.CalledProcessError as e:
        print(f"Error installing or starting service: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Install/Uninstall Monitor Mouse Mapper service")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall the service")
    args = parser.parse_args()

    if args.uninstall:
        uninstall_service()
        return
    
    # Check display server type early in the process
    check_display_server()
    
    # Call the install function
    install_service()


if __name__ == "__main__":
    main()
