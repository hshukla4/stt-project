#!/bin/bash

echo "🤖 Setting up OpenAI Integration"
echo "==============================="

echo "📋 Step 1: Install OpenAI dependencies..."
cd python
source venv/bin/activate
pip install openai python-dotenv

echo ""
echo "🔐 Step 2: Configure OpenAI API Key"
echo ""
echo "You need an OpenAI API key to use OpenAI Whisper."
echo "Get one from: https://platform.openai.com/api-keys"
echo ""
read -p "Enter your OpenAI API key (or press Enter to skip): " api_key

if [ -n "$api_key" ]; then
    # Update .env file with real API key
    sed -i.bak "s/your_openai_api_key_here/$api_key/" .env
    echo "✅ API key configured"
else
    echo "⚠️  Skipped API key setup - you can add it later to python/.env"
fi

echo ""
echo "🚀 Step 3: Start dual engine server..."
echo "Stopping any existing server..."
pkill -f "python.*server.py" 2>/dev/null

echo "Starting dual engine server..."
python server_dual.py &

echo ""
echo "✅ OpenAI integration setup complete!"
echo ""
echo "🎯 Available engines:"
echo "  - Local Whisper (runs on your computer)"
echo "  - OpenAI Whisper (uses OpenAI API)"
echo ""
echo "🔧 Configuration:"
echo "  - Primary engine: Local Whisper"
echo "  - Fallback engine: OpenAI Whisper"
echo "  - Dual engine mode: Enabled"
echo ""
echo "📱 Test at: http://localhost:8082/health"
