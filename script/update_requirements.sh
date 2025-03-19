#!/bin/bash

# This script updates the requirements.txt file using pip-tools
# Check if pip-tools is installed, if not install it
if ! pip show pip-tools > /dev/null 2>&1; then
    echo "pip-tools not found, installing..."
    pip install pip-tools
fi

# Compile the requirements.in to requirements.txt
echo "Compiling requirements.in to requirements.txt..."
pip-compile requirements.in

# Install the dependencies listed in requirements.txt
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Done!"