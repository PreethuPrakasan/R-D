#!/usr/bin/env python3
"""
Run the FastAPI backend from the project root
"""
import sys
import os

# Add the backend directory to the Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Change to backend directory
os.chdir(backend_path)

# Import and run the FastAPI app
import main
app = main.app
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Python FastAPI Backend...")
    print("📍 Backend URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔧 Health Check: http://localhost:8000/health")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
