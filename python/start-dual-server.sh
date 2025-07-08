#!/bin/bash

echo "🤖 Starting STT Dual Engine Server"
echo "=================================="

cd python

if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "🔍 Checking configuration..."
if [ -f ".env" ]; then
    source .env
    if [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        echo "⚠️  OpenAI API key not configured"
        echo "   Edit python/.env to add your API key"
        echo "   Or run: ./setup-openai.sh"
    else
        echo "✅ OpenAI API key configured"
    fi
else
    echo "⚠️  No .env file found"
fi

echo ""
echo "🚀 Starting dual engine server..."
echo "🔗 Local Whisper + OpenAI Whisper"
echo "📊 Health check: http://localhost:8082/health"
echo "📚 API docs: http://localhost:8082/docs"
echo ""
echo "💡 Press Ctrl+C to stop"

python server_dual.py
