# MonitorMouseMapper

## Introduction

Introducing **MonitorMouseMapper**, a Python-based solution designed to make your multi-monitor setup a seamless experience! This utility smartly manages your mouse movement when you have monitors with different resolutions, positioned above and below each other.

## Features

- 🖥️ **Automatic Monitor Detection**: Detects connected monitors and sets up your mouse to move smoothly between them.
- 🖱️ **Mouse Position Management**: Manages mouse pointer position intelligently when moving between monitors.
- ⚙️ **Custom Configuration**: Easy setup and customization via a JSON config file.
- 📐 **DPI Scaling**: Handles monitors with different DPIs elegantly.
- 🛡️ **Safety Regions**: Allows setting a "safety region" to avoid accidental jumps between monitors.
- 💼 **Plug-and-Play**: Automatic reconfiguration when a new monitor is connected.

## Installation

1. Clone the repository: 
    ```bash
    git clone https://github.com/yourusername/MonitorMouseMapper.git
    ```
2. Navigate to the project folder:
    ```bash
    cd MonitorMouseMapper
    ```
3. Run the script:
    ```bash
    python3 MonitorMouseMapper.py
    ```

## How to Use

1. **Initial Configuration**: On the first run, the script will ask you to pick your bottom and top monitors from a list of available options.
2. **Width Setup**: You'll be prompted to enter the width (in cm) of each monitor.
3. **Safety Region**: Optionally, you can set up a "safety region" in pixels to avoid accidental jumps.
4. **Run and Forget**: Once configured, the script will run in the background, taking care of your mouse movement.

## Requirements

- Python 3.x
- `pynput` library
- `xrandr` utility on Linux systems

## Troubleshooting

If you encounter any issues, you can:
- Check if `xrandr` is properly installed and up-to-date.
- Delete the `config.json` file and run the script again for a fresh configuration.
- Raise an issue on this GitHub repository.

## Contribution

Feel free to fork the project, open a pull request, or submit suggestions and bugs as GitHub issues.

## License

This project is open source, under the MIT license.

---

Make your multi-monitor life easier and more organized with **MonitorMouseMapper**! 🌟