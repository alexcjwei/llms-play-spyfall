#!/bin/bash
# Backend setup script

echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete! To activate the virtual environment, run:"
echo "source venv/bin/activate"
echo ""
echo "To start the development server, run:"
echo "uvicorn main:app --reload --host 0.0.0.0 --port 8000"