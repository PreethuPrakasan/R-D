@echo off
echo Starting Automotive AI Customer Service...

echo.
echo Checking if virtual environment exists...
if not exist "venv" (
    echo Virtual environment not found! Please run setup_python_env.bat first.
    pause
    exit /b 1
)

echo.
echo Starting Python FastAPI Backend...
start "Python Backend" cmd /k "cd /d %~dp0 && venv\Scripts\activate.bat && python start_backend.py"

echo.
echo Waiting for backend to start...
timeout /t 5 /nobreak > nul

echo.
echo Starting Node.js Twilio Server...
start "Node.js Server" cmd /k "cd /d %~dp0 && npm run dev"

echo.
echo Both servers are starting up!
echo Python Backend: http://localhost:8000
echo Node.js Server: http://localhost:5000
echo.
echo Press any key to exit...
pause > nul
