# MonitorMouseMapper
![Monitor Setup](images/full_setup_hills.png)
## Introduction

Make your multi-monitor life easier with **MonitorMouseMapper**! This Python-based utility eliminates the hassle of dealing with different monitor resolutions and DPIs. Designed specifically for setups where you have a high-DPI laptop monitor centered below a larger, lower-DPI external monitor.

## 🔥 Highlight: DPI Scaling Management

The core functionality of **MonitorMouseMapper** is to handle DPI scaling issues seamlessly as you move your mouse pointer between monitors with different DPIs. No more awkward jumps or stutters!

## Features

- 🖥️ **Automatic Monitor Detection**: No need for manual configuration. Automatically detects your monitors.
- 🖱️ **Smart Mouse Positioning**: Ensures your mouse moves smoothly between your top and bottom monitors.
- ⚙️ **Configuration File**: Customize your experience through a simple JSON config file.
- 🔄 **Dynamic Reconfiguration**: Automatically adapts when you connect or disconnect monitors.
- 🚀 **Desktop Integration**: Creates a desktop shortcut and application entry for easy access.

## Important Note

**X11 Session Required**: Monitor Mouse Mapper is designed for X11 and will not work properly on Wayland. Make sure to select "Ubuntu on Xorg" at the login screen.

## Quick Start Guide

1. **Install the utility**:
   ```bash
   # Clone the repository
   git clone https://github.com/Infraviored/MonitorMouseMapper.git
   cd MonitorMouseMapper

   # Run the installer script
   python3 install_service.py
   ```

2. **Configure your monitors**:
   - Launch the configurator via the desktop shortcut created during installation
   - OR open it from your applications menu
   - OR run it from terminal: `python3 ConfiguratorTool.py`

3. **Enjoy seamless mouse movement** between your monitors!

## Installation Details

The installer script automatically:
- Creates a Python virtual environment with all required dependencies
- Sets up a systemd user service to run at startup
- Creates desktop shortcuts and application entries
- Validates your monitor configuration

### Uninstalling

To uninstall Monitor Mouse Mapper:

```bash
python3 install_service.py --uninstall
```

## Managing the Service

Monitor Mouse Mapper runs as a systemd user service:

- **Check status**: `systemctl --user status monitor-mouse-mapper.service`
- **Start**: `systemctl --user start monitor-mouse-mapper.service`
- **Stop**: `systemctl --user stop monitor-mouse-mapper.service`
- **View logs**: `journalctl --user -u monitor-mouse-mapper.service -n 50`

## Troubleshooting

- **X11 vs Wayland**: Make sure you're using X11 (log out and select "Ubuntu on Xorg" at login)
- **Wrong Monitor Configuration**: Run the configurator tool if your monitor setup has changed
- **Service Not Starting**: Check logs with `journalctl --user -u monitor-mouse-mapper.service`

## Contribution

Contributions are welcome! Feel free to fork the project, submit pull requests, or raise issues.

## License

This project is licensed under the MIT license.

---

Simplify your multi-monitor setup with **MonitorMouseMapper**. Say goodbye to annoying DPI issues and hello to a smoother multi-monitor experience! 🌟
