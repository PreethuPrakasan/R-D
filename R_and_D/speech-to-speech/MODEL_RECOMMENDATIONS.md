# Model Recommendations for Low Latency

This document provides recommendations for faster models to reduce delay in your speech-to-speech pipeline.

## Current Setup
- **STT**: Vosk (vosk-model-small-en-us-0.15)
- **LLM**: Mistral 7B via Ollama
- **TTS**: pyttsx3 (system voices) or Coqui TTS

## 🎤 STT (Speech-to-Text) - Fastest Options

### 1. **Whisper.cpp** (Recommended for Speed)
- **Latency**: ~100-300ms (vs Vosk ~200-500ms)
- **Pros**: Very fast, good accuracy, supports streaming
- **Cons**: Requires compilation, larger model files
- **Installation**:
  ```bash
  pip install whisper-cpp-py
  ```
- **Model**: Use `tiny` or `base` for fastest inference

### 2. **Faster-Whisper** (Best Balance)
- **Latency**: ~150-400ms
- **Pros**: Faster than standard Whisper, good accuracy, easy to use
- **Cons**: Still slower than Vosk for very short clips
- **Installation**:
  ```bash
  pip install faster-whisper
  ```
- **Model**: Use `tiny` or `base` models

### 3. **Vosk (Optimized)** - Keep but optimize
- **Current**: vosk-model-small-en-us-0.15 (~40MB)
- **Faster option**: Use `vosk-model-en-us-0.22` (better accuracy) or keep small model
- **Optimization**: Already using small model, but ensure GPU acceleration if available

### 4. **Cloud APIs** (Fastest, but requires internet)
- **Google Speech-to-Text**: ~50-150ms latency
- **Azure Speech**: ~100-200ms latency
- **Pros**: Very fast, excellent accuracy
- **Cons**: Requires API keys, internet connection, costs money

## 🤖 LLM (Language Model) - Fastest Options

### 1. **Phi-3 Mini** (Best for Speed) ⭐ RECOMMENDED
- **Size**: 3.8B parameters
- **Latency**: ~200-500ms first token (vs Mistral ~2-5s)
- **Pros**: Very fast, good quality, small memory footprint
- **Installation**:
  ```bash
  ollama pull phi3:mini
  ```
- **Update code**: Change `model="mistral"` to `model="phi3:mini"` in `main.py`

### 2. **Llama 3 8B Instruct**
- **Size**: 8B parameters
- **Latency**: ~500ms-1.5s first token
- **Pros**: Better quality than Phi-3, still reasonably fast
- **Installation**:
  ```bash
  ollama pull llama3:8b-instruct
  ```

### 3. **Qwen2.5 7B Instruct**
- **Size**: 7B parameters
- **Latency**: ~400ms-1.2s first token
- **Pros**: Good multilingual support, fast inference
- **Installation**:
  ```bash
  ollama pull qwen2.5:7b-instruct
  ```

### 4. **GPU Acceleration** (Biggest Impact)
- If you have an NVIDIA GPU:
  ```bash
  # Install CUDA-enabled Ollama or use GPU-accelerated inference
  # This can reduce latency by 5-10x
  ```
- **Expected improvement**: 2-5s → 200-500ms for first token

### 5. **Model Quantization**
- Use quantized models (Q4, Q5) for faster inference
- Ollama automatically uses quantization, but you can specify:
  ```bash
  ollama pull phi3:mini-q4_0  # Even faster
  ```

## 🔊 TTS (Text-to-Speech) - Fastest Options

### 1. **Piper TTS** (Recommended) ⭐ BEST FOR SPEED
- **Latency**: ~50-200ms (vs pyttsx3 ~100-300ms, Coqui ~500ms-2s)
- **Pros**: Very fast, good quality, lightweight, offline
- **Installation**:
  ```bash
  pip install piper-tts
  ```
- **Models**: Download from [rhasspy/piper](https://github.com/rhasspy/piper)
- **Note**: Your class is named `PiperTTS` but currently uses Coqui/pyttsx3

### 2. **Edge TTS** (Cloud, but very fast)
- **Latency**: ~100-300ms
- **Pros**: Very fast, excellent quality, free, many voices
- **Cons**: Requires internet connection
- **Installation**:
  ```bash
  pip install edge-tts
  ```

### 3. **Coqui TTS (Faster Models)**
- **Current**: tacotron2-DDC (slow)
- **Faster options**:
  - `tts_models/en/ljspeech/glow-tts` - Faster, good quality
  - `tts_models/en/ljspeech/speedy-speech` - Very fast, lower quality
- **Optimization**: Use GPU if available

### 4. **pyttsx3 (Optimized)** - Current fallback
- Already fast but robotic
- Can increase speed: `engine.setProperty('rate', 200)` (current: 150)

## 🚀 Quick Wins (Easiest to Implement)

### Priority 1: Switch LLM to Phi-3 Mini
```bash
ollama pull phi3:mini
```
Then update `backend/main.py`:
```python
llm_engine = OllamaLLM(model="phi3:mini")  # Instead of "mistral"
```
**Expected improvement**: 2-5s → 200-500ms latency

### Priority 2: Implement Piper TTS
Replace the TTS implementation with actual Piper TTS (not Coqui).

### Priority 3: Use GPU if available
Enable GPU acceleration for LLM (biggest impact).

## 📊 Expected Latency Improvements

| Component | Current | With Optimizations | Improvement |
|-----------|---------|-------------------|-------------|
| STT (Vosk) | 200-500ms | 200-500ms | Keep (already fast) |
| LLM (Mistral) | 2-5s | 200-500ms (Phi-3) | **10x faster** |
| TTS (pyttsx3) | 100-300ms | 50-200ms (Piper) | 2x faster |
| **Total** | **2.3-5.8s** | **450-1200ms** | **~5x faster** |

## 🔧 Implementation Guide

### Step 1: Switch to Phi-3 Mini LLM
1. Pull the model: `ollama pull phi3:mini`
2. Update `backend/main.py` line 78: `model="phi3:mini"`
3. Restart backend

### Step 2: Implement Piper TTS
1. Install: `pip install piper-tts`
2. Download a model from [rhasspy/piper](https://github.com/rhasspy/piper)
3. Update `backend/tts/piper_tts.py` to use actual Piper TTS

### Step 3: (Optional) GPU Acceleration
- Install CUDA-enabled PyTorch if you have NVIDIA GPU
- Ollama will automatically use GPU if available

## 💡 Additional Optimizations

1. **Streaming**: Already implemented for LLM, can add for TTS
2. **Batch Processing**: Process multiple requests in parallel
3. **Caching**: Cache common responses
4. **Model Quantization**: Use Q4/Q5 quantized models
5. **Reduce Context Window**: Limit conversation history to last 5-10 messages

## 📝 Notes

- **Phi-3 Mini** is the single biggest improvement (10x faster LLM)
- **Piper TTS** is the best balance of speed and quality for TTS
- **GPU acceleration** provides the biggest overall improvement if available
- Keep **Vosk** for STT - it's already quite fast and accurate



