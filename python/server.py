from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import whisper
import tempfile
import os
import shutil
from pathlib import Path
import logging
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="STT Dual Engine Server", description="Local Whisper + OpenAI Whisper")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
whisper_model = None
openai_client = None
MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

@app.on_event("startup")
async def startup_event():
    """Load Whisper model and initialize OpenAI"""
    global whisper_model, openai_client
    
    # Load local Whisper
    try:
        logger.info(f"Loading Whisper model: {MODEL_SIZE}")
        whisper_model = whisper.load_model(MODEL_SIZE)
        logger.info("Whisper model loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        whisper_model = None
    
    # Initialize OpenAI
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key and openai_api_key != "your_openai_api_key_here":
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=openai_api_key)
            # Test connection
            models = openai_client.models.list()
            logger.info("OpenAI client initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            openai_client = None
    else:
        logger.info("OpenAI API key not configured")

@app.get("/health")
async def health_check():
    """Health check with engine status"""
    return {
        "status": "healthy",
        "model_loaded": whisper_model is not None,
        "model_size": MODEL_SIZE,
        "engines": {
            "local_whisper": whisper_model is not None,
            "openai_whisper": openai_client is not None
        }
    }

@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(default="auto"),
    engines: str = Form(default="both")  # both, local, openai
):
    """Transcribe with both engines for comparison"""
    
    if not whisper_model:
        raise HTTPException(status_code=503, detail="Whisper model not loaded")
    
    if not audio.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio.filename).suffix) as temp_file:
        try:
            shutil.copyfileobj(audio.file, temp_file)
            temp_path = temp_file.name
            
            logger.info(f"Transcribing {audio.filename} with engines: {engines}")
            
            # Prepare language options
            options = {}
            if language and language != "auto":
                lang_map = {"en-IN": "en", "hi-IN": "hi", "gu-IN": "gu"}
                options["language"] = lang_map.get(language, language)
            
            results = {}
            
            # Local Whisper transcription
            if engines in ["both", "local"] and whisper_model:
                try:
                    logger.info("Running local Whisper transcription...")
                    local_result = whisper_model.transcribe(temp_path, **options)
                    results["local_whisper"] = {
                        "text": local_result["text"].strip(),
                        "language_detected": local_result.get("language", "unknown"),
                        "confidence": "N/A",
                        "engine": "local_whisper",
                        "model_size": MODEL_SIZE,
                        "status": "success"
                    }
                except Exception as e:
                    logger.error(f"Local Whisper failed: {e}")
                    results["local_whisper"] = {
                        "text": f"Local Whisper failed: {str(e)}",
                        "status": "error",
                        "engine": "local_whisper"
                    }
            
            # OpenAI Whisper transcription
            if engines in ["both", "openai"] and openai_client:
                try:
                    logger.info("Running OpenAI Whisper transcription...")
                    with open(temp_path, "rb") as audio_file:
                        transcript = openai_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language=options.get("language") if options.get("language") else None
                        )
                    
                    results["openai_whisper"] = {
                        "text": transcript.text.strip(),
                        "language_detected": options.get("language", "auto-detected"),
                        "confidence": "N/A",
                        "engine": "openai_whisper",
                        "model": "whisper-1",
                        "status": "success"
                    }
                except Exception as e:
                    logger.error(f"OpenAI Whisper failed: {e}")
                    results["openai_whisper"] = {
                        "text": f"OpenAI Whisper failed: {str(e)}",
                        "status": "error",
                        "engine": "openai_whisper"
                    }
            elif engines in ["both", "openai"] and not openai_client:
                results["openai_whisper"] = {
                    "text": "OpenAI not configured - add API key to python/.env",
                    "status": "not_configured",
                    "engine": "openai_whisper"
                }
            
            # If only one engine requested, return that format
            if engines == "local" and "local_whisper" in results:
                return results["local_whisper"]
            elif engines == "openai" and "openai_whisper" in results:
                return results["openai_whisper"]
            
            # Return dual results
            return {
                "engines": results,
                "dual_mode": True,
                "filename": audio.filename
            }
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "STT Dual Engine Server",
        "local_whisper": whisper_model is not None,
        "openai_whisper": openai_client is not None,
        "endpoints": {
            "health": "/health",
            "transcribe": "/transcribe (POST)",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
