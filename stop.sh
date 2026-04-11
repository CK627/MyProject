#!/bin/bash

# Find PID of web_monitor_server.py
PID=$(pgrep -f "web_monitor_server.py")

if [ -z "$PID" ]; then
    echo "Web Monitor is not running."
    exit 1
fi

echo "Stopping Web Monitor (PID: $PID)..."
kill $PID

# Wait for process to exit
while kill -0 $PID 2>/dev/null; do
    sleep 0.5
done

echo "Stopped successfully."
