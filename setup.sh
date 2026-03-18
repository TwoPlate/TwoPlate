#!/bin/bash
# NZ Industrial Property Finder — setup script
# Run once to install all dependencies.

set -e

echo "=== NZ Industrial Property Finder Setup ==="
echo

# Check Python version
python3 --version || { echo "Python 3 is required. Install it from https://python.org"; exit 1; }

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browser (Chromium only — for JS-rendered sites)
echo "Installing Playwright browser (Chromium)..."
playwright install chromium

echo
echo "=== Setup complete! ==="
echo
echo "To run the app:"
echo "  source .venv/bin/activate"
echo "  streamlit run app.py"
echo
echo "The app will open in your browser at http://localhost:8501"
