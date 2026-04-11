#!/bin/bash

# Check python version
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 could not be found."
    exit 1
fi

echo "Detected python3."

# Check if pip is installed
if ! python3 -m pip --version &> /dev/null; then
    echo "pip not found. Attempting to install pip..."
    if command -v yum &> /dev/null; then
        yum install -y python3-pip
    elif command -v apt-get &> /dev/null; then
        apt-get install -y python3-pip
    else
        echo "Could not install pip. Please install python3-pip manually."
        exit 1
    fi
fi

echo "Installing dependencies..."

# Upgrade pip
python3 -m pip install --upgrade pip

# Install dependencies compatible with Python 3.6
# requests < 2.28 for Python 3.6 support
# Pillow < 9.0.0 for Python 3.6 support
python3 -m pip install "requests<2.28" "Pillow<9.0.0" pystray schedule

echo "Installation complete."
