"""
RunPod Serverless Handler for WhisperX
Transcription with speaker diarization
"""

import os
import gc
import torch
import whisperx
import runpod
import requests
import tempfile
from urllib.parse import urlparse

# Configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
BATCH_SIZE = 16  # Reduce if low on GPU memory
MODEL_NAME = os.environ.get("WHISPER_MODEL", "large-v2")
HF_TOKEN = os.environ.get("HF_TOKEN", None)

# Pre-load models at startup for faster inference
print(f"Loading WhisperX model: {MODEL_NAME} on {DEVICE}...")
whisper_model = whisperx.load_model(
    MODEL_NAME, 
    device=DEVICE, 
    compute_type=COMPUTE_TYPE,
    language=None  # Auto-detect language
)
print("WhisperX model loaded successfully!")

# Pre-load diarization model if HF_TOKEN is available
diarize_model = None
if HF_TOKEN:
    print("Loading diarization model...")
    from whisperx.diarize import DiarizationPipeline
    diarize_model = DiarizationPipeline(use_auth_token=HF_TOKEN, device=DEVICE)
    print("Diarization model loaded successfully!")
else:
    print("WARNING: No HF_TOKEN provided. Diarization will be disabled.")
    print("Set HF_TOKEN environment variable to enable speaker diarization.")


def download_audio(url: str) -> str:
    """Download audio from URL to temporary file."""
    print(f"Downloading audio from: {url}")
    
    # Parse URL to get filename extension
    parsed = urlparse(url)
    path = parsed.path
    ext = os.path.splitext(path)[1] or ".mp3"
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    
    # Download with streaming
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()
    
    for chunk in response.iter_content(chunk_size=8192):
        temp_file.write(chunk)
    
    temp_file.close()
    print(f"Audio downloaded to: {temp_file.name}")
    return temp_file.name


def transcribe_audio(audio_path: str, options: dict) -> dict:
    """
    Transcribe audio with WhisperX and optional diarization.
    
    Args:
        audio_path: Path to audio file
        options: Dict with optional keys:
            - language: Language code (e.g., 'en', 'fr'). Auto-detect if None.
            - diarize: Enable speaker diarization (default: True)
            - min_speakers: Minimum number of speakers
            - max_speakers: Maximum number of speakers
            - batch_size: Batch size for inference
    
    Returns:
        Dict with transcription results
    """
    # Extract options
    language = options.get("language", None)
    enable_diarize = options.get("diarize", True)
    min_speakers = options.get("min_speakers", None)
    max_speakers = options.get("max_speakers", None)
    batch_size = options.get("batch_size", BATCH_SIZE)
    
    print(f"Starting transcription... (language={language}, diarize={enable_diarize})")
    
    # Load audio
    audio = whisperx.load_audio(audio_path)
    
    # 1. Transcribe with Whisper
    print("Step 1/3: Transcribing with Whisper...")
    result = whisper_model.transcribe(
        audio, 
        batch_size=batch_size,
        language=language
    )
    
    detected_language = result.get("language", language or "unknown")
    print(f"Detected language: {detected_language}")
    
    # 2. Align whisper output
    print("Step 2/3: Aligning transcription...")
    try:
        model_a, metadata = whisperx.load_align_model(
            language_code=detected_language, 
            device=DEVICE
        )
        result = whisperx.align(
            result["segments"], 
            model_a, 
            metadata, 
            audio, 
            DEVICE, 
            return_char_alignments=False
        )
        
        # Clean up alignment model
        del model_a
        gc.collect()
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
            
    except Exception as e:
        print(f"Warning: Alignment failed for language {detected_language}: {e}")
        print("Continuing without alignment...")
    
    # 3. Speaker diarization
    if enable_diarize and diarize_model is not None:
        print("Step 3/3: Performing speaker diarization...")
        try:
            diarize_kwargs = {}
            if min_speakers is not None:
                diarize_kwargs["min_speakers"] = min_speakers
            if max_speakers is not None:
                diarize_kwargs["max_speakers"] = max_speakers
            
            diarize_segments = diarize_model(audio, **diarize_kwargs)
            result = whisperx.assign_word_speakers(diarize_segments, result)
            print("Diarization completed successfully!")
            
        except Exception as e:
            print(f"Warning: Diarization failed: {e}")
            print("Continuing without diarization...")
    else:
        print("Step 3/3: Skipping diarization (disabled or no HF_TOKEN)")
    
    # Format output
    output = {
        "language": detected_language,
        "segments": result.get("segments", []),
        "word_segments": result.get("word_segments", [])
    }
    
    # Create simple text output
    full_text = " ".join([seg.get("text", "").strip() for seg in output["segments"]])
    output["text"] = full_text
    
    # Create speaker-formatted output if diarization was performed
    if any("speaker" in seg for seg in output["segments"]):
        speaker_text = []
        current_speaker = None
        current_text = []
        
        for seg in output["segments"]:
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "").strip()
            
            if speaker != current_speaker:
                if current_text:
                    speaker_text.append(f"[{current_speaker}]: {' '.join(current_text)}")
                current_speaker = speaker
                current_text = [text]
            else:
                current_text.append(text)
        
        if current_text:
            speaker_text.append(f"[{current_speaker}]: {' '.join(current_text)}")
        
        output["speaker_text"] = "\n".join(speaker_text)
    
    return output


def handler(job: dict) -> dict:
    """
    RunPod handler function.
    
    Expected input format:
    {
        "input": {
            "audio": "https://example.com/audio.mp3",
            "language": "en",  # optional
            "diarize": true,   # optional, default: true
            "min_speakers": 2, # optional
            "max_speakers": 4, # optional
            "batch_size": 16   # optional
        }
    }
    """
    job_input = job.get("input", {})
    
    # Validate input
    audio_url = job_input.get("audio")
    if not audio_url:
        return {"error": "Missing 'audio' field in input. Please provide an audio URL."}
    
    audio_path = None
    try:
        # Download audio
        audio_path = download_audio(audio_url)
        
        # Extract options
        options = {
            "language": job_input.get("language"),
            "diarize": job_input.get("diarize", True),
            "min_speakers": job_input.get("min_speakers"),
            "max_speakers": job_input.get("max_speakers"),
            "batch_size": job_input.get("batch_size", BATCH_SIZE),
        }
        
        # Transcribe
        result = transcribe_audio(audio_path, options)
        
        return {
            "status": "success",
            "output": result
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to download audio: {str(e)}"}
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    finally:
        # Cleanup temporary file
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"Cleaned up temporary file: {audio_path}")


# Start RunPod serverless handler
if __name__ == "__main__":
    print("Starting RunPod WhisperX handler...")
    runpod.serverless.start({"handler": handler})
