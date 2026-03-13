#!/bin/bash

echo "Starting Automotive AI Customer Service..."

echo ""
echo "Checking if virtual environment exists..."
if [ ! -d "venv" ]; then
    echo "Virtual environment not found! Please run setup_python_env.sh first."
    exit 1
fi

echo ""
echo "Starting Python FastAPI Backend..."
source venv/bin/activate
python start_backend.py &
BACKEND_PID=$!

echo ""
echo "Waiting for backend to start..."
sleep 5

echo ""
echo "Starting Node.js Twilio Server..."
npm run dev &
NODE_PID=$!

echo ""
echo "Both servers are starting up!"
echo "Python Backend: http://localhost:8000"
echo "Node.js Server: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $NODE_PID 2>/dev/null
    exit 0
}

# Trap Ctrl+C
trap cleanup SIGINT

# Wait for both processes
wait
