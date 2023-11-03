#!/bin/bash


# Determine the current path of this script
CURRENT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Define the desktop entry
DESKTOP_ENTRY="[Desktop Entry]
Name=MonitorMouseMapper
Exec=/usr/bin/python3 $CURRENT_PATH/MonitorMouseMapper.py
Icon=$CURRENT_PATH/images/icon_hills.png
Terminal=false
Type=Application
Categories=Utility;Application
"

# Ensure the applications directory exists
APPLICATIONS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPLICATIONS_DIR"

# Specify the filename for the desktop entry
DESKTOP_ENTRY_FILENAME="$APPLICATIONS_DIR/MonitorMouseMapper.desktop"

# Create the desktop entry file
echo "$DESKTOP_ENTRY" > "$DESKTOP_ENTRY_FILENAME"

# Make the desktop entry file executable
chmod +x "$DESKTOP_ENTRY_FILENAME"

echo "Desktop entry created at $DESKTOP_ENTRY_FILENAME"
