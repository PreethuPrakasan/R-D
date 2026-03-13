#!/bin/bash

echo "Starting Speech-to-Speech Backend..."
echo ""

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Please run setup.py first."
    exit 1
fi

# Change to backend directory
cd backend

# Start the server
python main.py

