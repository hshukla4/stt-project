# STT Server with Guaranteed English Translation

A FastAPI-based speech-to-text server that provides guaranteed English translation of multilingual audio input using OpenAI Whisper and GPT-4.

## 🌟 Features

- **Multilingual Speech Recognition**: Supports Hindi, Gujarati, and other languages
- **Dual Engine Processing**: Uses both local Whisper and OpenAI Whisper API
- **Guaranteed English Output**: GPT-4 translation ensures accurate English results
- **Improved Gujarati Handling**: Multiple detection strategies for better accuracy
- **Real-time Processing**: Fast audio transcription and translation
- **RESTful API**: Easy integration with any frontend

## 🏗️ Architecture

```
Audio Input → Whisper Transcription → GPT-4 Translation → English Output
     ↓              ↓                      ↓                ↓
  .webm/.wav    Original Language      English Text     JSON Response
```

### Processing Flow

1. **Audio Reception**: Receives audio files via HTTP POST
2. **Multi-Language Detection**: 
   - Auto-detection attempt
   - Forced Gujarati transcription
   - Forced Hindi transcription
   - Selects best result based on quality metrics
3. **GPT-4 Translation**: Translates transcribed text to English
4. **Response Formatting**: Returns structured JSON with original and translated text

## 🚀 Installation

### Prerequisites

- Python 3.8+
- OpenAI API key
- FFmpeg (for audio processing)

### Dependencies

```bash
pip install fastapi uvicorn whisper openai python-multipart
```

### Setup

1. **Clone and setup environment:**
```bash
git clone <repository>
cd stt-project/server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Set OpenAI API key:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

3. **Start the server:**
```bash
python server.py
```

Server will start on `http://localhost:8082`

## 📚 API Documentation

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "message": "STT Server with Guaranteed English Translation",
  "method": "Whisper transcribe + GPT-4 translate",
  "guaranteed": "English output via GPT-4",
  "languages": "Improved Gujarati and Hindi handling"
}
```

### Transcribe Audio
```http
POST /transcribe
Content-Type: multipart/form-data

audio: <audio_file>
engines: "both" | "local" | "openai" (optional, default: "both")
```

**Response:**
```json
{
  "filename": "recording.webm",
  "engines": "both",
  "results": {
    "local_whisper": {
      "text": "I want to listen to Shiva hymns.",
      "original_text": "મને શિવભજન સાંભળવું છે.",
      "detected_language": "gu",
      "method": "Local Whisper (Multi-language) + GPT-4 Translation",
      "success": true,
      "alternatives": {
        "auto": {"text": "...", "language": "gu"},
        "gujarati": {"text": "...", "language": "gu"},
        "hindi": {"text": "...", "language": "hi"}
      }
    },
    "openai_whisper": {
      "text": "I want to listen to Shiva hymns.",
      "original_text": "મને શિવભજન સાંભળવું છે.",
      "method": "OpenAI Whisper + GPT-4 Translation",
      "success": true
    }
  },
  "best_result": "I want to listen to Shiva hymns.",
  "note": "🌍 Both engines with improved Gujarati handling + GPT-4 translation"
}
```

### Alternative Endpoints

- `POST /translate` - Alias for `/transcribe`
- `POST /dual-transcribe` - Forces both engines

## 🔧 Code Architecture

### Core Components

#### 1. Audio Processing (`transcribe_with_local_whisper`)
```python
async def transcribe_with_local_whisper(file_path: str) -> dict:
    # Multi-strategy transcription approach
    
    # Strategy 1: Auto-detection
    result_auto = whisper_model.transcribe(file_path)
    
    # Strategy 2: Force Gujarati
    result_gujarati = whisper_model.transcribe(file_path, language="gu")
    
    # Strategy 3: Force Hindi  
    result_hindi = whisper_model.transcribe(file_path, language="hi")
    
    # Quality-based selection logic
    best_text = choose_best_transcription(auto, gujarati, hindi)
    
    # Translation to English
    english_text = await translate_with_gpt(best_text)
```

**Why this approach?**
- Gujarati and Hindi share similar phonetics
- Auto-detection often misclassifies languages
- Multiple attempts improve accuracy
- Quality metrics (length, confidence) guide selection

#### 2. GPT-4 Translation (`translate_with_gpt`)
```python
async def translate_with_gpt(text: str) -> str:
    # Smart English detection
    if text.isascii() and not contains_indian_words(text):
        return text  # Already English
    
    # GPT-4 translation request
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "system", 
            "content": "Professional translator. Hindi/Gujarati → English."
        }, {
            "role": "user", 
            "content": f"Translate: {text}"
        }]
    )
```

**Why GPT-4 for translation?**
- More context-aware than Whisper's built-in translation
- Handles cultural nuances (भजन → hymn/bhajan)
- Better error recovery for garbled transcriptions
- Consistent English output regardless of input quality

#### 3. Result Selection Logic
```python
# Quality-based selection
if len(gujarati_text) > len(auto_text) and len(gujarati_text) > 5:
    best_text = gujarati_text
elif len(hindi_text) > len(auto_text) and len(hindi_text) > 5:
    best_text = hindi_text
else:
    best_text = auto_text
```

**Selection criteria:**
- **Length**: Longer transcriptions often more complete
- **Minimum threshold**: Avoids empty/garbage results
- **Language preference**: Gujarati → Hindi → Auto
- **Fallback logic**: Always returns some result

## 🛠️ Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY="sk-..."

# Optional
WHISPER_MODEL="base"  # tiny, base, small, medium, large
SERVER_PORT="8082"
LOG_LEVEL="INFO"
```

### Model Selection

```python
# Available Whisper models (trade-off: speed vs accuracy)
whisper_model = whisper.load_model("base")  # Recommended
# Options: tiny, base, small, medium, large
```

### CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Customize for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🐛 Debugging

### Common Issues

1. **No transcription output**
   - Check audio file format (supported: wav, webm, mp3, m4a)
   - Verify microphone permissions
   - Check audio file size (< 25MB for OpenAI)

2. **Poor Gujarati accuracy**
   - Try speaking more slowly/clearly
   - Check logs for alternative transcriptions
   - Consider using Hindi if more accurate

3. **OpenAI API errors**
   - Verify API key is set correctly
   - Check API quota/billing
   - Monitor rate limits

### Debugging Logs

Enable verbose logging to see transcription attempts:

```python
logging.basicConfig(level=logging.DEBUG)
```

Look for these log patterns:
```
INFO: Auto detection: '...' (detected: gu)
INFO: Gujarati forced: '...'
INFO: Hindi forced: '...'  
INFO: Final choice: '...' (language: gu)
INFO: GPT Translation result: '...'
```

## 🔒 Security Considerations

- **API Key Protection**: Never commit API keys to version control
- **Input Validation**: File size and type restrictions implemented
- **CORS Policy**: Restrict origins in production
- **Rate Limiting**: Consider implementing for production use

## 📈 Performance

### Benchmarks (typical)

- **Local Whisper**: ~2-5 seconds for 5-second audio
- **OpenAI Whisper**: ~1-3 seconds for 5-second audio  
- **GPT-4 Translation**: ~1-2 seconds
- **Total Pipeline**: ~3-8 seconds end-to-end

### Optimization Tips

1. **Use smaller Whisper models** for faster processing
2. **Cache translations** for common phrases
3. **Implement async processing** for multiple requests
4. **Use GPU** for local Whisper (if available)

## 🚀 Production Deployment

### Docker Setup

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8082

CMD ["uvicorn", "dual-server:app", "--host", "0.0.0.0", "--port", "8082"]
```

### Environment Setup

```bash
# Production environment variables
OPENAI_API_KEY="sk-..."
WHISPER_MODEL="small"  # Balance speed/accuracy
LOG_LEVEL="WARNING"    # Reduce log verbosity
CORS_ORIGINS="https://yourdomain.com"
```

## 📝 Changelog

### v2.0.0 - Enhanced Gujarati Support
- ✅ Multi-strategy language detection
- ✅ GPT-4 translation integration
- ✅ Improved error handling
- ✅ Quality-based result selection

### v1.0.0 - Initial Release
- ✅ Basic Whisper transcription
- ✅ OpenAI API integration
- ✅ FastAPI server setup

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues and questions:
- Check the [debugging section](#-debugging)
- Review server logs for error details
- Open an issue with audio sample and error logs


