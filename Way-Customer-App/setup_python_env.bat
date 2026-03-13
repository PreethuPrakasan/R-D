@echo off
echo Setting up Python virtual environment for Automotive AI Backend...

echo.
echo Creating virtual environment...
python -m venv venv

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing Python dependencies...
echo Installing basic dependencies first...
pip install fastapi==0.104.1
pip install uvicorn==0.24.0
pip install pydantic==2.5.0
pip install python-dotenv==1.0.0
pip install httpx==0.25.2
pip install python-multipart==0.0.6

echo.
echo Installing PostgreSQL drivers...
echo Trying asyncpg first...
pip install asyncpg==0.29.0 || (
    echo asyncpg installation failed, trying alternative...
    pip install psycopg2-binary==2.9.9
)

echo.
echo Python environment setup complete!
echo.
echo To activate the environment manually, run:
echo venv\Scripts\activate.bat
echo.
echo To start the backend, run:
echo python start_backend.py
echo.
pause
