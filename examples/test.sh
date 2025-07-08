#!/bin/bash
echo "🎤 STT API Examples"
echo "=================="

echo "1. Health check:"
curl -s http://localhost:8082/health

echo -e "\n2. API info:"
curl -s http://localhost:8082/

echo -e "\n3. Test transcription:"
echo "curl -X POST 'http://localhost:8082/transcribe' \\"
echo "     -F 'audio=@your_file.wav' \\"
echo "     -F 'language=auto'"

echo -e "\n📚 Full docs: http://localhost:8082/docs"
