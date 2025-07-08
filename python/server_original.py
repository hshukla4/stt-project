from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import whisper
import tempfile
import os
import shutil
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="STT Server", description="Speech-to-Text with Whisper")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
whisper_model = None
MODEL_SIZE = "base"  # Options: tiny, base, small, medium, large

@app.on_event("startup")
async def startup_event():
    """Load Whisper model on startup"""
    global whisper_model
    try:
        logger.info(f"Loading Whisper model: {MODEL_SIZE}")
        whisper_model = whisper.load_model(MODEL_SIZE)
        logger.info("Whisper model loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        whisper_model = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": whisper_model is not None,
        "model_size": MODEL_SIZE
    }

@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(default="auto")
):
    """Transcribe uploaded audio file"""
    
    if not whisper_model:
        raise HTTPException(status_code=503, detail="Whisper model not loaded")
    
    # Validate file type
    if not audio.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio.filename).suffix) as temp_file:
        try:
            # Save uploaded file
            shutil.copyfileobj(audio.file, temp_file)
            temp_path = temp_file.name
            
            logger.info(f"Transcribing file: {audio.filename}")
            
            # Prepare transcription options
            options = {}
            if language and language != "auto":
                # Convert language codes
                lang_map = {
                    "en-IN": "en",
                    "hi-IN": "hi", 
                    "gu-IN": "gu"
                }
                options["language"] = lang_map.get(language, language)
            
            # Transcribe with Whisper
            result = whisper_model.transcribe(temp_path, **options)
            
            # Return results
            response = {
                "text": result["text"].strip(),
                "language_detected": result.get("language", "unknown"),
                "confidence": "N/A",  # Whisper doesn't provide confidence scores
                "engine": "whisper",
                "model_size": MODEL_SIZE
            }
            
            logger.info(f"Transcription completed: {len(result['text'])} characters")
            return response
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "STT Server is running",
        "model_loaded": whisper_model is not None,
        "endpoints": {
            "health": "/health",
            "transcribe": "/transcribe (POST)",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
