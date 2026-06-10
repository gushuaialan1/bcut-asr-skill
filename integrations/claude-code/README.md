# Claude Code Agent SDK Integration

## Quick Install

```bash
# 1. Install the Python package
pip install bcut-asr-skill

# 2. Add to your Claude Code agent's tools
# Copy the tool definitions below into your agent config
```

## Tool Definitions

Add these to your Claude Code agent's `tools` configuration:

### ASR Tool — Transcribe Audio

```json
{
  "name": "bcut_asr_transcribe",
  "description": "Transcribe audio/video file to subtitles using Bilibili BCut ASR service. Supports SRT, LRC, TXT, JSON output formats.",
  "input_schema": {
    "type": "object",
    "properties": {
      "file_path": {
        "type": "string",
        "description": "Path to audio or video file. Supports: mp3, wav, flac, aac, m4a, mp4 (auto ffmpeg extraction)"
      },
      "output_format": {
        "type": "string",
        "enum": ["srt", "lrc", "txt", "json"],
        "default": "srt",
        "description": "Output subtitle format"
      },
      "output_path": {
        "type": "string",
        "description": "Optional output file path. If not provided, returns text directly."
      }
    },
    "required": ["file_path"]
  }
}
```

### TTS Tool — Synthesize Speech

```json
{
  "name": "bcut_tts_synthesize",
  "description": "Synthesize speech from text using Bilibili BCut TTS service. 100+ voices available.",
  "input_schema": {
    "type": "object",
    "properties": {
      "text": {
        "type": "string",
        "description": "Text to synthesize (Chinese recommended)"
      },
      "output_path": {
        "type": "string",
        "description": "Output WAV file path"
      },
      "voice": {
        "type": "string",
        "default": "dingzhen",
        "description": "Voice identifier. Use 'list_voices' to see all options."
      },
      "pitch": {
        "type": "integer",
        "default": 0,
        "minimum": -300,
        "maximum": 300,
        "description": "Pitch adjustment"
      },
      "speed": {
        "type": "integer",
        "default": 0,
        "minimum": -300,
        "maximum": 300,
        "description": "Speed adjustment"
      },
      "volume": {
        "type": "integer",
        "default": 100,
        "minimum": 0,
        "maximum": 100,
        "description": "Volume level"
      }
    },
    "required": ["text", "output_path"]
  }
}
```

### TTS Tool — List Voices

```json
{
  "name": "bcut_tts_list_voices",
  "description": "List all available TTS voices with categories and metadata.",
  "input_schema": {
    "type": "object",
    "properties": {}
  }
}
```

## Python Handler

```python
from bcut_asr_skill import BCutASRClient, BCutTTSClient, OutputFormat

def bcut_asr_transcribe(file_path: str, output_format: str = "srt", output_path: str = None):
    """ASR transcribe tool handler"""
    client = BCutASRClient()
    fmt = OutputFormat[output_format.upper()]
    result = client.transcribe(file_path, output_format=fmt)
    
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        return {"status": "success", "output_path": output_path}
    return {"status": "success", "text": result}

def bcut_tts_synthesize(text: str, output_path: str, voice: str = "dingzhen", 
                        pitch: int = 0, speed: int = 0, volume: int = 100):
    """TTS synthesize tool handler"""
    client = BCutTTSClient()
    path = client.synthesize(text, output_path, voice=voice, 
                             pitch=pitch, speed=speed, volume=volume)
    return {"status": "success", "output_path": path}

def bcut_tts_list_voices():
    """TTS list voices tool handler"""
    client = BCutTTSClient()
    voices = client.list_voices()
    return {
        "categories": [
            {
                "title": cat.title,
                "voices": [
                    {"name": v.name, "voice": v.voice, "engine": v.voice_engine}
                    for v in cat.materials
                ]
            }
            for cat in voices
        ]
    }
```

## Usage Example

```python
# In your Claude Code agent:

# User: "Transcribe this meeting recording"
# Agent calls: bcut_asr_transcribe(file_path="meeting.mp3", output_format="srt")

# User: "Generate a voiceover with the news anchor voice"
# Agent calls: bcut_tts_list_voices()
# Then: bcut_tts_synthesize(text="Breaking news...", output_path="voiceover.wav", voice="presenter_male")
```
