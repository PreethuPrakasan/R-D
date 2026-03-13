"""
Script to download required models for ASR and TTS
"""
import os
import requests
import zipfile
import tarfile
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"

def download_file(url: str, destination: Path):
    """Download a file with progress"""
    logger.info(f"Downloading {url}...")
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    with open(destination, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\rProgress: {percent:.1f}%", end='', flush=True)
    
    print()  # New line after progress
    logger.info(f"Downloaded to {destination}")

def extract_zip(zip_path: Path, extract_to: Path):
    """Extract ZIP file"""
    logger.info(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    logger.info("Extraction complete")

def download_vosk_model():
    """Download Vosk ASR model"""
    models_dir = Path(__file__).parent.parent / "models" / "vosk"
    model_dir = models_dir / VOSK_MODEL_NAME
    
    if model_dir.exists():
        logger.info(f"Vosk model already exists at {model_dir}")
        return str(model_dir)
    
    zip_path = models_dir / f"{VOSK_MODEL_NAME}.zip"
    
    try:
        download_file(VOSK_MODEL_URL, zip_path)
        extract_zip(zip_path, models_dir)
        
        # Remove zip file
        zip_path.unlink()
        
        logger.info(f"Vosk model ready at {model_dir}")
        return str(model_dir)
    except Exception as e:
        logger.error(f"Error downloading Vosk model: {e}")
        logger.info("You can manually download from: https://alphacephei.com/vosk/models")
        return None

def main():
    """Main function"""
    print("="*60)
    print("Model Download Script")
    print("="*60)
    
    print("\n1. Downloading Vosk ASR model...")
    vosk_path = download_vosk_model()
    
    print("\n" + "="*60)
    print("Model Download Complete!")
    print("="*60)
    
    if vosk_path:
        print(f"\nVosk model location: {vosk_path}")
    else:
        print("\nPlease download models manually:")
        print("- Vosk: https://alphacephei.com/vosk/models")
        print("- Piper models will be downloaded automatically on first use")

if __name__ == "__main__":
    main()

