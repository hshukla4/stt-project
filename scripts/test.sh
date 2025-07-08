#!/bin/bash
echo "🧪 Testing installation..."

source venv/bin/activate

python -c "
try:
    import fastapi
    import whisper
    print('✅ All imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
"
