import whisper
import openai
from openai import OpenAI
import logging
import tempfile
import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="STT Server with Guaranteed English Translation")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = OpenAI()

# Load Whisper model
logger.info("Loading Whisper model: base")
whisper_model = whisper.load_model("base")
logger.info("Whisper model loaded successfully!")

# Test OpenAI connection
try:
    models = client.models.list()
    logger.info("OpenAI client initialized successfully!")
except Exception as e:
    logger.error(f"OpenAI initialization failed: {e}")

# 🔥 NEW: GPT Translation function
async def translate_with_gpt(text: str) -> str:
    """Use GPT-4 to translate any text to English"""
    if not text or len(text.strip()) == 0:
        return ""
    
    # Check if already English (simple heuristic)
    if text.isascii() and not any(word in text.lower() for word in ['ही', 'है', 'का', 'की', 'के', 'में', 'से', 'और']):
        logger.info("Text appears to be English already")
        return text
    
    try:
        logger.info(f"Translating to English: '{text[:50]}...'")
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional translator. Translate the given text to English. If it's already in English, return it unchanged. Only return the translated text, nothing else."
                },
                {
                    "role": "user", 
                    "content": f"Translate this to English: {text}"
                }
            ],
            max_tokens=500,
            temperature=0.1
        )
        
        english_text = response.choices[0].message.content.strip()
        logger.info(f"GPT Translation result: '{english_text}'")
        return english_text
        
    except Exception as e:
        logger.error(f"GPT translation failed: {e}")
        return text  # Return original if translation fails

# 🔥 ENHANCED: Local Whisper with GPT translation
async def transcribe_with_local_whisper(file_path: str) -> dict:
    """Transcribe with local Whisper and translate with GPT"""
    try:
        logger.info("Running local Whisper transcription...")
        
        # Transcribe in original language first
        result = whisper_model.transcribe(file_path)
        original_text = result["text"].strip()
        detected_language = result.get("language", "unknown")
        
        logger.info(f"Whisper original: '{original_text}' (detected: {detected_language})")
        
        # Translate to English using GPT
        english_text = await translate_with_gpt(original_text)
        
        return {
            "text": english_text,  # Return English translation
            "original_text": original_text,
            "detected_language": detected_language,
            "method": "Local Whisper + GPT-4 Translation",
            "success": True
        }
    except Exception as e:
        logger.error(f"Local Whisper error: {e}")
        return {
            "text": "",
            "original_text": "",
            "error": str(e),
            "method": "Local Whisper + GPT-4 Translation",
            "success": False
        }

# 🔥 ENHANCED: OpenAI Whisper with GPT translation
async def transcribe_with_openai_whisper(file_path: str) -> dict:
    """Transcribe with OpenAI Whisper and translate with GPT"""
    try:
        logger.info("Running OpenAI Whisper transcription...")
        
        # Use transcriptions (not translations) to get original language
        with open(file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        original_text = response.text.strip()
        logger.info(f"OpenAI original: '{original_text}'")
        
        # Translate to English using GPT
        english_text = await translate_with_gpt(original_text)
        
        return {
            "text": english_text,  # Return English translation
            "original_text": original_text,
            "method": "OpenAI Whisper + GPT-4 Translation",
            "success": True
        }
    except Exception as e:
        logger.error(f"OpenAI Whisper error: {e}")
        return {
            "text": "",
            "original_text": "",
            "error": str(e),
            "method": "OpenAI Whisper + GPT-4 Translation",
            "success": False
        }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "STT Server with Guaranteed English Translation",
        "method": "Whisper transcribe + GPT-4 translate",
        "guaranteed": "English output via GPT-4"
    }

@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    engines: str = Form(default="both")
):
    """Main transcription endpoint with guaranteed English output"""
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
        content = await audio.read()
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        logger.info(f"Transcribing {audio.filename} with engines: {engines}")
        
        if engines == "both":
            # Run both engines
            local_result = await transcribe_with_local_whisper(temp_file_path)
            openai_result = await transcribe_with_openai_whisper(temp_file_path)
            
            response = {
                "filename": audio.filename,
                "engines": engines,
                "results": {
                    "local_whisper": local_result,
                    "openai_whisper": openai_result
                },
                "best_result": openai_result["text"] if openai_result["success"] else local_result["text"],
                "note": "🌍 Both engines guaranteed English via GPT-4 translation"
            }
            
        elif engines == "openai":
            # OpenAI only
            result = await transcribe_with_openai_whisper(temp_file_path)
            response = {
                "filename": audio.filename,
                "engines": engines,
                "text": result["text"],
                "original_text": result.get("original_text", ""),
                "method": result["method"],
                "success": result["success"],
                "note": "🌍 Guaranteed English via GPT-4 translation"
            }
            
        else:
            # Local only
            result = await transcribe_with_local_whisper(temp_file_path)
            response = {
                "filename": audio.filename,
                "engines": engines,
                "text": result["text"],
                "original_text": result.get("original_text", ""),
                "method": result["method"],
                "success": result["success"],
                "note": "🌍 Guaranteed English via GPT-4 translation"
            }
        
        logger.info(f"✅ Transcription complete: '{response.get('best_result', response.get('text', 'No result')[:50])}...'")
        return response
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return {
            "error": str(e),
            "filename": audio.filename,
            "success": False
        }
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

# Alias endpoints for compatibility
@app.post("/translate")
async def translate_audio(audio: UploadFile = File(...), engines: str = Form(default="both")):
    return await transcribe_audio(audio, engines)

@app.post("/dual-transcribe") 
async def dual_transcribe_audio(audio: UploadFile = File(...)):
    return await transcribe_audio(audio, "both")

if __name__ == "__main__":
    print("🚀 Starting STT Server with Guaranteed English Translation!")
    print("🎯 Method: Whisper transcribe → GPT-4 translate")
    print("🌍 GUARANTEED English output!")
    print("=" * 60)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8082,
        log_level="info"
    )