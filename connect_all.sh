#!/bin/bash
# Script to open connections to all team_3 VMs in separate terminals

# Function to detect the terminal emulator
detect_terminal() {
    # Print debug info
    echo "Debug: OSTYPE=$OSTYPE"
    echo "Debug: uname=$(uname)"
    
    # Check for macOS using multiple methods
    if [ "$(uname)" = "Darwin" ]; then
        # macOS detected using uname
        echo "open -a Terminal"
    elif [ "$OSTYPE" = "darwin"* ] || [[ "$OSTYPE" == darwin* ]]; then
        # macOS detected using OSTYPE
        echo "open -a Terminal"
    elif command -v gnome-terminal &> /dev/null; then
        echo "gnome-terminal --"
    elif command -v konsole &> /dev/null; then
        echo "konsole -e"
    elif command -v xterm &> /dev/null; then
        echo "xterm -e"
    else
        echo ""
    fi
}

# For macOS, we can directly check using uname before trying the function
if [ "$(uname)" = "Darwin" ]; then
    TERMINAL="open -a Terminal"
    echo "Debug: macOS detected using uname, setting TERMINAL to: $TERMINAL"
else
    TERMINAL=$(detect_terminal)
    echo "Debug: Terminal detection result: $TERMINAL"
fi

if [ -z "$TERMINAL" ]; then
    echo "Error: Could not detect terminal emulator. Please connect to VMs manually."
    echo "You can manually connect using:"
    echo "  - ./connect_bastion.sh (to connect to the bastion host)"
    echo "  - ./connect_vm.sh <number> (to connect to a specific VM)"
    exit 1
fi

echo "Opening connections to all VMs in separate terminals..."

# Connect to bastion host
$TERMINAL ./connect_bastion.sh &

# Wait a bit for the bastion connection to establish
sleep 2

# Connect to each VM
for ((i=1; i<=5; i++)); do
    $TERMINAL ./connect_vm.sh $i &
    sleep 1
done

echo "Connection windows opened for bastion host and 5 VMs."
