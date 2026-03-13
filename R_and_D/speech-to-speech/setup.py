"""
Setup script for Speech-to-Speech application
"""
import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Step: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    
    if result.stdout:
        print(result.stdout)
    
    return True

def main():
    """Main setup function"""
    print("="*60)
    print("Speech-to-Speech Application Setup")
    print("="*60)
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("Error: Python 3.10 or higher is required")
        sys.exit(1)
    
    # Create virtual environment
    venv_path = Path("venv")
    if not venv_path.exists():
        print("\nCreating virtual environment...")
        if not run_command(f"{sys.executable} -m venv venv", "Create virtual environment"):
            print("Failed to create virtual environment")
            sys.exit(1)
    else:
        print("Virtual environment already exists")
    
    # Determine activation script
    if sys.platform == "win32":
        activate_script = "venv\\Scripts\\activate"
        pip_command = "venv\\Scripts\\pip"
        python_command = "venv\\Scripts\\python"
    else:
        activate_script = "source venv/bin/activate"
        pip_command = "venv/bin/pip"
        python_command = "venv/bin/python"
    
    # Install backend dependencies
    print("\nInstalling backend dependencies...")
    backend_req = Path("backend/requirements.txt")
    if backend_req.exists():
        if sys.platform == "win32":
            if not run_command(f"{pip_command} install -r backend/requirements.txt", "Install Python packages"):
                print("Failed to install backend dependencies")
                sys.exit(1)
        else:
            if not run_command(f"{pip_command} install -r backend/requirements.txt", "Install Python packages"):
                print("Failed to install backend dependencies")
                sys.exit(1)
    else:
        print("Warning: backend/requirements.txt not found")
    
    # Install frontend dependencies
    print("\nInstalling frontend dependencies...")
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        if sys.platform == "win32":
            if not run_command("cd frontend && npm install", "Install Node.js packages"):
                print("Failed to install frontend dependencies")
                print("Please run 'cd frontend && npm install' manually")
        else:
            if not run_command("cd frontend && npm install", "Install Node.js packages"):
                print("Failed to install frontend dependencies")
                print("Please run 'cd frontend && npm install' manually")
    else:
        print("Warning: frontend directory not found")
    
    # Create models directory
    models_dir = Path("backend/models")
    models_dir.mkdir(parents=True, exist_ok=True)
    (models_dir / "vosk").mkdir(exist_ok=True)
    (models_dir / "piper").mkdir(exist_ok=True)
    
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Activate virtual environment:")
    if sys.platform == "win32":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("\n2. Install Ollama from https://ollama.ai")
    print("3. Pull a model: ollama pull mistral")
    print("4. Download Vosk model (optional, will auto-download):")
    print("   https://alphacephei.com/vosk/models")
    print("\n5. Start backend: cd backend && python main.py")
    print("6. Start frontend: cd frontend && npm start")
    print("\n" + "="*60)

if __name__ == "__main__":
    main()

