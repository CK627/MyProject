#!/bin/bash

# Ensure we are in the script's directory
cd "$(dirname "$0")"

echo "Restarting Web Monitor..."

# Stop the existing process
if [ -f "stop.sh" ]; then
    ./stop.sh
else
    # Fallback if stop.sh is missing (though it should be there)
    PID=$(ps aux | grep "[w]eb_monitor_server.py" | awk '{print $2}')
    if [ -n "$PID" ]; then
        echo "Stopping existing process (PID: $PID)..."
        kill $PID
        sleep 1
    fi
fi

# Wait a moment to ensure port is released
sleep 1

# Start the new process
if [ -f "start.sh" ]; then
    ./start.sh
else
    echo "Error: start.sh not found!"
    exit 1
fi

echo "Restart complete!"
