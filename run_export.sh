#!/bin/bash

# Navigate to the script directory (optional but helpful)
cd "$(dirname "$0")"

# Step 1: Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# Step 2: Activate the virtual environment
source venv/bin/activate

# Step 3: Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Step 4: Run your script
echo "Running export_website.py..."
python3 export_website.py