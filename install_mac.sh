#!/bin/bash
echo "Installing App Locker dependencies..."
pip3 install psutil
echo ""
echo "Installation complete!"
echo "Run './start_locker.sh' to start the App Locker."
echo ""
echo "NOTE: You may need to grant Accessibility permissions:"
echo "System Preferences > Security & Privacy > Privacy > Accessibility"
echo "Add Terminal (or iTerm) to the list"
