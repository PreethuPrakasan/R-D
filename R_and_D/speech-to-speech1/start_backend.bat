@echo off
echo Starting Speech-to-Speech Backend...
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Please run setup.py first.
    pause
    exit /b 1
)

REM Change to backend directory
cd backend

REM Start the server
python main.py

pause

