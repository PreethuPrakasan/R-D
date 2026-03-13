# Setup Notes - Virtual Environment

## Issue Fixed

The original `requirements.txt` had compatibility issues with Python 3.13.5:
- **TTS (Coqui)** version 0.22.0 doesn't support Python 3.13 (requires <3.12)
- Fixed by making TTS optional and using `pyttsx3` as fallback

## Solution Applied

1. **Updated `requirements.txt`**:
   - Changed from exact versions (`==`) to minimum versions (`>=`) for better compatibility
   - Made TTS (Coqui) optional with a note
   - Added `pyaudio` back to requirements

2. **TTS Fallback System**:
   - The application will try Coqui TTS first
   - If unavailable (like with Python 3.13), it automatically falls back to `pyttsx3`
   - `pyttsx3` uses system voices (Windows SAPI5, Linux espeak, Mac built-in)

## Installed Packages

All required packages are now installed in the virtual environment:

✅ **Core Framework:**
- fastapi (0.122.0)
- uvicorn (0.38.0)
- websockets (15.0.1)
- pydantic (2.12.4)

✅ **ASR (Speech Recognition):**
- vosk (0.3.45)
- pyaudio (0.2.14) - for microphone input

✅ **TTS (Text-to-Speech):**
- pyttsx3 (2.99) - system voices (works on all platforms)
- TTS (Coqui) - optional, not installed (not compatible with Python 3.13)

✅ **Other Dependencies:**
- requests, numpy, sounddevice, aiofiles, etc.

## Using Virtual Environment

### Always activate the virtual environment before running commands:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### Running Commands

**Install packages:**
```bash
# Windows
venv\Scripts\pip.exe install package_name

# Linux/Mac (after activation)
pip install package_name
```

**Run Python scripts:**
```bash
# Windows
venv\Scripts\python.exe script.py

# Linux/Mac (after activation)
python script.py
```

**Start backend:**
```bash
# Windows
venv\Scripts\python.exe backend\main.py

# Or use the script:
start_backend.bat
```

## TTS Behavior

The application will work with `pyttsx3` (system voices) which is already installed. This provides:
- **Windows**: Uses SAPI5 voices (built-in, good quality)
- **Linux**: Requires `espeak` (install: `sudo apt-get install espeak`)
- **Mac**: Uses built-in voices

If you want to use Coqui TTS (better quality), you'll need:
1. Python 3.11 or earlier (Coqui TTS doesn't support 3.13 yet)
2. Install separately: `pip install TTS`

## Next Steps

1. ✅ Virtual environment created
2. ✅ Dependencies installed
3. ⏭️ Download Vosk model (will auto-download on first use, or run `python backend/scripts/download_models.py`)
4. ⏭️ Install Ollama and pull a model: `ollama pull mistral`
5. ⏭️ Start the backend: `venv\Scripts\python.exe backend\main.py`
6. ⏭️ Start the frontend: `cd frontend && npm start`

## Troubleshooting

**If you get "module not found" errors:**
- Ensure virtual environment is activated
- Reinstall: `venv\Scripts\pip.exe install -r backend\requirements.txt`

**If TTS doesn't work:**
- `pyttsx3` should work automatically on Windows
- Check console logs for TTS initialization messages
- The app will show which TTS engine is being used

**If microphone doesn't work:**
- Check Windows microphone permissions
- Verify `pyaudio` is installed: `venv\Scripts\pip.exe list | findstr pyaudio`

