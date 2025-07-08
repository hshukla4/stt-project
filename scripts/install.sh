#!/bin/bash
echo "🔧 Installing STT dependencies..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Installation complete!"
echo ""
echo "🚀 To start:"
echo "1. source venv/bin/activate"
echo "2. python src/stt_server.py"
