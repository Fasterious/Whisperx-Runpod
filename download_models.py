"""
Pre-download models during Docker build to speed up cold starts.
This script downloads WhisperX, alignment, and diarization models.
"""

import os
import torch
import whisperx

# Configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
MODEL_NAME = os.environ.get("WHISPER_MODEL", "large-v2")
HF_TOKEN = os.environ.get("HF_TOKEN", None)

print(f"Device: {DEVICE}")
print(f"Compute type: {COMPUTE_TYPE}")
print(f"Model: {MODEL_NAME}")

# 1. Download Whisper model
print(f"\n[1/4] Downloading Whisper model: {MODEL_NAME}...")
model = whisperx.load_model(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE)
del model
print("Whisper model downloaded successfully!")

# 2. Download common alignment models
print("\n[2/4] Downloading alignment models for common languages...")
LANGUAGES = ["en", "fr", "de", "es", "it"]

for lang in LANGUAGES:
    try:
        print(f"  Downloading alignment model for '{lang}'...")
        model_a, metadata = whisperx.load_align_model(language_code=lang, device=DEVICE)
        del model_a
        print(f"  ✓ Alignment model for '{lang}' downloaded!")
    except Exception as e:
        print(f"  ✗ Could not download alignment model for '{lang}': {e}")

# 3. Download VAD model (used by WhisperX internally)
print("\n[3/4] VAD model is bundled with WhisperX...")
print("VAD ready!")

# 4. Download diarization model if HF_TOKEN is available
if HF_TOKEN:
    print("\n[4/4] Downloading diarization models...")
    try:
        from whisperx.diarize import DiarizationPipeline
        diarize_model = DiarizationPipeline(use_auth_token=HF_TOKEN, device=DEVICE)
        del diarize_model
        print("Diarization models downloaded successfully!")
    except Exception as e:
        print(f"Warning: Could not download diarization models: {e}")
        print("Diarization will still work at runtime if HF_TOKEN is provided.")
else:
    print("\n[4/4] Skipping diarization model download (no HF_TOKEN provided)")
    print("You can provide HF_TOKEN at runtime for diarization.")

print("\n" + "="*50)
print("All models downloaded successfully!")
print("="*50)

# Force CUDA cache cleanup
if DEVICE == "cuda":
    import gc
    gc.collect()
    torch.cuda.empty_cache()
