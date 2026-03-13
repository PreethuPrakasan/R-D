#!/usr/bin/env python3
"""
Startup script for the Python FastAPI backend
"""
import uvicorn
import sys
import os

# Check if virtual environment is activated
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("⚠️  WARNING: Virtual environment not detected!")
    print("Please run setup_python_env.bat (Windows) or setup_python_env.sh (Linux/Mac) first")
    print("Or manually activate the virtual environment:")
    print("  Windows: venv\\Scripts\\activate.bat")
    print("  Linux/Mac: source venv/bin/activate")
    sys.exit(1)

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

if __name__ == "__main__":
    print("🚀 Starting Python FastAPI Backend...")
    print("📍 Backend URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔧 Health Check: http://localhost:8000/health")
    print("")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
