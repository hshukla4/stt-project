# STT Client - React Frontend

A modern React application that provides a user-friendly interface for multilingual speech-to-text with guaranteed English translation.

## 🌟 Features

- **🎤 Real-time Audio Recording**: Browser-based microphone access
- **🌍 Multilingual Support**: Optimized for Hindi and Gujarati input
- **⚡ Live Translation**: Instant English translation display
- **🎨 Beautiful UI**: Clean, responsive interface with status indicators
- **📱 Mobile Friendly**: Works on desktop and mobile browsers
- **🔄 Dual Engine Display**: Shows results from both Whisper engines
- **📊 Detailed Results**: Original text, translation, and processing metadata

## 🏗️ Architecture

```
Microphone → Audio Recording → WAV Encoding → Server API → Results Display
     ↓            ↓               ↓             ↓            ↓
  getUserMedia  Float32Array   Blob/FormData  HTTP POST   React State
```

### Component Flow

1. **Audio Capture**: Uses Web Audio API for high-quality recording
2. **Real-time Processing**: Converts audio to WAV format
3. **Server Communication**: Sends audio to backend via REST API
4. **Result Display**: Shows original text and English translation
5. **State Management**: React hooks for seamless UI updates

## 🚀 Installation

### Prerequisites

- Node.js 16+
- npm or yarn
- Modern browser with microphone support

### Setup

1. **Create React app:**
```bash
npx create-react-app stt-frontend
cd stt-frontend
```

2. **Install dependencies:**
```bash
npm install
# No additional dependencies required - uses vanilla React
```

3. **Replace default files:**
```bash
# Copy the provided files:
# - src/App.js
# - src/DualTranscriber.js  
# - src/index.js
# - public/index.html
```

4. **Start development server:**
```bash
npm start
```

Application will open at `http://localhost:3000`

## 📁 Project Structure

```
src/
├── App.js              # Main application component
├── DualTranscriber.js  # Core STT functionality
├── index.js           # React entry point
└── index.css          # Global styles

public/
├── index.html         # HTML template with custom styles
└── favicon.ico        # Application icon
```

## 🔧 Component Architecture

### App.js
```javascript
// Simple wrapper component
function App() {
  return (
    <div className="App">
      <DualTranscriber />  {/* Main functionality */}
    </div>
  );
}
```

**Purpose**: Minimal wrapper for future extensibility (routing, global state, etc.)

### DualTranscriber.js - Core Component

#### State Management
```javascript
const [status, setStatus] = useState('idle');        // recording | processing | idle
const [results, setResults] = useState(null);        // API response data
const [msg, setMsg] = useState('');                  // User feedback messages
const [audioURL, setAudioURL] = useState(null);      // Blob URL for playback
```

**State Flow:**
```
idle → recording → processing → idle (with results)
  ↑                               ↓
  ←←←← User clicks stop ←←←←←←←←←←←←
```

#### Audio Recording System

##### 1. Audio Setup (`startRec`)
```javascript
const startRec = async () => {
  // Request microphone access
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  
  // Create audio context with 16kHz sample rate (optimal for Whisper)
  const ctx = new AudioContext({ sampleRate: 16000 });
  
  // Create audio processing pipeline
  const src = ctx.createMediaStreamSource(stream);      // Input source
  const proc = ctx.createScriptProcessor(4096, 1, 1);   // Audio processor
  
  // Capture audio data in real-time
  proc.onaudioprocess = e => {
    chunksRef.current.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  };
};
```

**Why this approach?**
- **16kHz sampling**: Matches Whisper's expected input format
- **Float32Array chunks**: High-quality audio data preservation
- **ScriptProcessor**: Real-time audio capture (though deprecated, still widely supported)
- **Single channel**: Reduces file size, sufficient for speech

##### 2. Audio Processing (`mergeBuffers`, `encodeWAV`)
```javascript
const mergeBuffers = buffers => {
  // Concatenate all audio chunks into single array
  const length = buffers.reduce((sum, b) => sum + b.length, 0);
  const out = new Float32Array(length);
  let offset = 0;
  buffers.forEach(b => { out.set(b, offset); offset += b.length; });
  return out;
};

const encodeWAV = (samples, sampleRate = 16000) => {
  // Create WAV file header (44 bytes)
  const buf = new ArrayBuffer(44 + samples.length*2);
  const view = new DataView(buf);
  
  // WAV format specifications
  writeString(0, 'RIFF');                    // File type
  view.setUint32(4, 36 + samples.length*2); // File size
  writeString(8, 'WAVE');                    // File format
  // ... format chunk and data chunk
  
  return new Blob([view], { type: 'audio/wav' });
};
```

**Technical Details:**
- **WAV format**: Uncompressed, compatible with all audio systems
- **16-bit encoding**: Good quality with reasonable file size
- **Little-endian**: Standard byte order for WAV files
- **Blob creation**: Enables file upload to server

#### Server Communication

##### 1. API Request (`stopRec`)
```javascript
const stopRec = async () => {
  // Create audio blob
  const wavBlob = encodeWAV(mergeBuffers(chunksRef.current));
  
  // Prepare form data
  const form = new FormData();
  form.append('audio', wavBlob, 'recording.wav');
  
  // Send to server
  const response = await fetch('http://localhost:8082/transcribe', { 
    method: 'POST', 
    body: form 
  });
  
  const result = await response.json();
  processServerResponse(result);
};
```

**Why FormData?**
- **Multipart encoding**: Required for file uploads
- **Binary support**: Preserves audio data integrity
- **Standard format**: Compatible with FastAPI/most backends

##### 2. Response Processing
```javascript
// Parse new server format
setResults({
  type: 'new_format',
  data: result,
  best_result: result.best_result || result.text || 'No result',
  original_text: result.results?.openai_whisper?.original_text || 
                result.results?.local_whisper?.original_text || '',
  local_whisper: result.results?.local_whisper || {},
  openai_whisper: result.results?.openai_whisper || {},
  method: result.results?.openai_whisper?.method || 'Whisper + GPT-4 Translation'
});
```

**Response Structure Handling:**
- **Flexible parsing**: Works with different server response formats
- **Fallback logic**: Graceful handling of missing fields
- **Engine separation**: Displays results from both processing engines

#### UI Rendering System

##### 1. Recording Controls
```javascript
<button
  onClick={() => status==='idle'? startRec() : stopRec()}
  disabled={status==='processing'}
  style={{
    background: status==='recording'? 'crimson' : 
               status==='processing'? 'orange' : '#16a34a',
    // ... responsive styling
  }}
>
  {status==='recording'? '■' : 
   status==='processing' ? '⏳' : '🎤'}
</button>
```

**Visual Feedback:**
- **Color coding**: Green (ready) → Red (recording) → Orange (processing)
- **Icon changes**: Microphone → Stop → Loading
- **Disabled states**: Prevents user errors during processing

##### 2. Results Display (`renderResults`)
```javascript
const renderResults = () => {
  if (!results) return null;
  
  return (
    <div>
      {/* English Translation - Primary Result */}
      <div style={{ background: '#e6ffe6', border: '2px solid #16a34a' }}>
        <h5>✅ English Translation</h5>
        <pre>{results.best_result}</pre>
      </div>
      
      {/* Original Text - Secondary Info */}
      {results.original_text && (
        <div style={{ background: '#f0f9ff', border: '2px solid #3b82f6' }}>
          <h5>📝 Original Text</h5>
          <pre>{results.original_text}</pre>
        </div>
      )}
      
      {/* Processing Method - Metadata */}
      <div style={{ background: '#fef3c7', border: '2px solid #f59e0b' }}>
        <h5>🔧 Processing Method</h5>
        <div>{results.method}</div>
      </div>
    </div>
  );
};
```

**Information Hierarchy:**
1. **English translation** (most important) - prominent green styling
2. **Original text** (context) - blue styling for reference
3. **Processing metadata** (technical) - yellow styling for details

## 🎨 Styling System

### Design Philosophy

- **Functional over decorative**: Every element serves a purpose
- **Status-driven colors**: Visual feedback for user actions
- **Mobile-first**: Responsive design for all devices
- **Accessibility**: High contrast, clear typography

### Color Scheme

```css
/* Status Colors */
--success: #16a34a    /* Green - completed, ready */
--warning: #f59e0b    /* Orange - processing, caution */
--error: #dc2626      /* Red - recording, errors */
--info: #3b82f6       /* Blue - information, metadata */

/* Background Gradients */
body {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
```

### Responsive Components

```javascript
// Adaptive button sizing
style={{
  width: 120, height: 120,              // Desktop: Large click target
  '@media (max-width: 768px)': {        // Mobile: Adjust for touch
    width: 100, height: 100
  }
}}
```

## 📱 Browser Compatibility

### Supported Features

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| getUserMedia | ✅ | ✅ | ✅ | ✅ |
| AudioContext | ✅ | ✅ | ✅ | ✅ |
| ScriptProcessor | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| FormData Upload | ✅ | ✅ | ✅ | ✅ |

**Note**: ScriptProcessor is deprecated but still supported. Future versions will migrate to AudioWorklet.

### Mobile Considerations

```javascript
// iOS Safari requires user interaction before audio context
const startRec = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // Handle iOS audio context limitations
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }
  } catch (e) {
    // Graceful fallback for permission denied
    setMsg('❌ Microphone access denied');
  }
};
```

## 🔧 Configuration

### API Endpoint

```javascript
// Development
const API_BASE = 'http://localhost:8082';

// Production
const API_BASE = process.env.REACT_APP_API_URL || 'https://api.yourdomain.com';
```

### Audio Settings

```javascript
const AUDIO_CONFIG = {
  sampleRate: 16000,        // Optimal for Whisper
  channels: 1,              // Mono recording
  bufferSize: 4096,         // Balance latency/quality
  format: 'wav'             // Universal compatibility
};
```

## 🐛 Debugging

### Common Issues

1. **Microphone permission denied**
   ```javascript
   // Check browser settings, try HTTPS
   navigator.permissions.query({name: 'microphone'})
   ```

2. **Audio context errors**
   ```javascript
   // Ensure user interaction before creating context
   document.addEventListener('click', () => {
     if (audioContext.state === 'suspended') {
       audioContext.resume();
     }
   });
   ```

3. **CORS errors**
   ```javascript
   // Ensure server allows frontend origin
   // Check browser developer console for details
   ```

### Debug Tools

```javascript
// Enable verbose logging
const DEBUG = process.env.NODE_ENV === 'development';

if (DEBUG) {
  console.log('Audio chunks:', chunksRef.current.length);
  console.log('WAV blob size:', wavBlob.size);
  console.log('Server response:', result);
}
```

## 🚀 Performance Optimization

### Memory Management

```javascript
// Clean up audio resources
const cleanup = async () => {
  if (procRef.current) procRef.current.disconnect();
  if (srcRef.current) srcRef.current.disconnect();
  if (ctxRef.current) await ctxRef.current.close();
  
  // Clear audio chunks to free memory
  chunksRef.current = [];
};
```

### File Size Optimization

```javascript
// Compress audio for faster uploads (optional)
const compressAudio = (samples) => {
  // Reduce sample rate for smaller files
  const targetRate = 8000;  // vs 16000 default
  const compression = 16000 / targetRate;
  // ... downsampling logic
};
```

## 🔒 Security Considerations

### Data Privacy

- **No persistent storage**: Audio data never saved locally
- **Temporary blobs**: Cleaned up after processing
- **HTTPS required**: For microphone access in production

### Input Validation

```javascript
// File size limits
const MAX_AUDIO_SIZE = 25 * 1024 * 1024; // 25MB
if (wavBlob.size > MAX_AUDIO_SIZE) {
  throw new Error('Audio file too large');
}

// Duration limits
const MAX_DURATION = 300; // 5 minutes
if (recordingDuration > MAX_DURATION) {
  throw new Error('Recording too long');
}
```

## 📈 Future Enhancements

### Planned Features

- **🔄 Live streaming mode**: Real-time transcription
- **📊 Confidence scores**: Display transcription confidence
- **🎵 Multiple formats**: MP3, OGG support
- **💾 Export options**: Download transcripts
- **🌙 Dark mode**: User preference themes

### Technical Roadmap

1. **AudioWorklet migration**: Replace deprecated ScriptProcessor
2. **WebRTC integration**: Better audio quality
3. **Progressive Web App**: Offline functionality
4. **Voice activity detection**: Automatic start/stop

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone <repository>
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

### Code Style

- **ES6+ features**: Arrow functions, async/await, destructuring
- **Functional components**: Hooks over class components
- **Inline styles**: For dynamic styling (status-dependent)
- **Semantic HTML**: Accessible markup

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.