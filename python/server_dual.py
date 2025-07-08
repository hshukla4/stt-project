from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import whisper
import tempfile
import os
import shutil
from pathlib import Path
import logging
from dotenv import load_dotenv
import openai
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="STT Dual Engine Server", description="Speech-to-Text with Local Whisper + OpenAI")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
local_whisper_model = None
openai_client = None
MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
PRIMARY_ENGINE = os.getenv("PRIMARY_ENGINE", "local_whisper")
FALLBACK_ENGINE = os.getenv("FALLBACK_ENGINE", "openai_whisper")
ENABLE_DUAL_ENGINE = os.getenv("ENABLE_DUAL_ENGINE", "true").lower() == "true"

@app.on_event("startup")
async def startup_event():
    """Load models on startup"""
    global local_whisper_model, openai_client
    
    # Load local Whisper model
    try:
        logger.info(f"Loading local Whisper model: {MODEL_SIZE}")
        local_whisper_model = whisper.load_model(MODEL_SIZE)
        logger.info("Local Whisper model loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load local Whisper model: {e}")
        local_whisper_model = None
    
    # Initialize OpenAI client
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key and openai_api_key != "your_openai_api_key_here":
        try:
            openai_client = OpenAI(api_key=openai_api_key)
            # Test the connection
            models = openai_client.models.list()
            logger.info("OpenAI client initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            openai_client = None
    else:
        logger.warning("OpenAI API key not provided")
        openai_client = None

@app.get("/health")
async def health_check():
    """Enhanced health check with dual engine status"""
    return {
        "status": "healthy",
        "engines": {
            "local_whisper": {
                "available": local_whisper_model is not None,
                "model_size": MODEL_SIZE if local_whisper_model else None
            },
            "openai_whisper": {
                "available": openai_client is not None,
                "model": "whisper-1" if openai_client else None
            }
        },
        "primary_engine": PRIMARY_ENGINE,
        "fallback_engine": FALLBACK_ENGINE if ENABLE_DUAL_ENGINE else None,
        "dual_engine_enabled": ENABLE_DUAL_ENGINE
    }

@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(default="auto"),
    engine: str = Form(default="auto")  # auto, local, openai
):
    """Transcribe audio with dual engine support"""
    
    if not audio.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    # Determine which engine to use
    if engine == "auto":
        if PRIMARY_ENGINE == "local_whisper" and local_whisper_model:
            selected_engine = "local_whisper"
        elif PRIMARY_ENGINE == "openai_whisper" and openai_client:
            selected_engine = "openai_whisper"
        elif local_whisper_model:
            selected_engine = "local_whisper"
        elif openai_client:
            selected_engine = "openai_whisper"
        else:
            raise HTTPException(status_code=503, detail="No transcription engines available")
    else:
        selected_engine = f"{engine}_whisper"
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio.filename).suffix) as temp_file:
        try:
            shutil.copyfileobj(audio.file, temp_file)
            temp_path = temp_file.name
            
            logger.info(f"Transcribing {audio.filename} with {selected_engine}")
            
            # Try primary engine
            try:
                if selected_engine == "local_whisper" and local_whisper_model:
                    result = await transcribe_with_local_whisper(temp_path, language)
                elif selected_engine == "openai_whisper" and openai_client:
                    result = await transcribe_with_openai(temp_path, language)
                else:
                    raise Exception(f"Engine {selected_engine} not available")
                
                result["engine_used"] = selected_engine
                return result
                
            except Exception as primary_error:
                logger.error(f"Primary engine {selected_engine} failed: {primary_error}")
                
                # Try fallback engine if dual engine is enabled
                if ENABLE_DUAL_ENGINE and FALLBACK_ENGINE:
                    try:
                        logger.info(f"Trying fallback engine: {FALLBACK_ENGINE}")
                        
                        if FALLBACK_ENGINE == "local_whisper" and local_whisper_model:
                            result = await transcribe_with_local_whisper(temp_path, language)
                        elif FALLBACK_ENGINE == "openai_whisper" and openai_client:
                            result = await transcribe_with_openai(temp_path, language)
                        else:
                            raise Exception(f"Fallback engine {FALLBACK_ENGINE} not available")
                        
                        result["engine_used"] = f"{FALLBACK_ENGINE} (fallback)"
                        result["primary_engine_error"] = str(primary_error)
                        return result
                        
                    except Exception as fallback_error:
                        logger.error(f"Fallback engine failed: {fallback_error}")
                        raise HTTPException(status_code=500, detail=f"Both engines failed. Primary: {primary_error}, Fallback: {fallback_error}")
                else:
                    raise HTTPException(status_code=500, detail=f"Transcription failed: {primary_error}")
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

async def transcribe_with_local_whisper(temp_path: str, language: str):
    """Transcribe using local Whisper model"""
    options = {}
    if language and language != "auto":
        lang_map = {"en-IN": "en", "hi-IN": "hi", "gu-IN": "gu"}
        options["language"] = lang_map.get(language, language)
    
    result = local_whisper_model.transcribe(temp_path, **options)
    
    return {
        "text": result["text"].strip(),
        "language_detected": result.get("language", "unknown"),
        "confidence": "N/A",
        "engine": "local_whisper",
        "model_size": MODEL_SIZE
    }

async def transcribe_with_openai(temp_path: str, language: str):
    """Transcribe using OpenAI Whisper API"""
    with open(temp_path, "rb") as audio_file:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language if language != "auto" else None
        )
    
    return {
        "text": transcript.text.strip(),
        "language_detected": language if language != "auto" else "auto-detected",
        "confidence": "N/A",
        "engine": "openai_whisper",
        "model": "whisper-1"
    }

@app.get("/engines")
async def get_engines():
    """Get available engines status"""
    return {
        "local_whisper": {
            "available": local_whisper_model is not None,
            "model_size": MODEL_SIZE,
            "status": "loaded" if local_whisper_model else "not_loaded"
        },
        "openai_whisper": {
            "available": openai_client is not None,
            "model": "whisper-1",
            "status": "connected" if openai_client else "not_configured"
        }
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "STT Dual Engine Server",
        "engines_available": {
            "local_whisper": local_whisper_model is not None,
            "openai_whisper": openai_client is not None
        },
        "endpoints": {
            "health": "/health",
            "transcribe": "/transcribe (POST)",
            "engines": "/engines",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
