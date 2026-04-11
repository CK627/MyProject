#!/bin/bash

# Check if script is already running
PID=$(pgrep -f "web_monitor_server.py")

if [ -n "$PID" ]; then
    echo "Web Monitor is already running (PID: $PID)"
    exit 1
fi

echo "Starting Web Monitor Server..."
nohup python3 web_monitor_server.py > /dev/null 2>&1 &

NEW_PID=$!
echo "Started successfully!"
echo "PID: $NEW_PID"
echo "Log output: (Disabled)"
echo "Web Interface: http://localhost:2442"
