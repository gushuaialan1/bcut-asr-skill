# OpenClaw Integration

## Quick Setup

```bash
# Install the Python package
pip install bcut-asr-skill

# Add to OpenClaw workspace tools
# Copy the MCP server config below
```

## MCP Server Config

Add to your OpenClaw `mcpServers` configuration:

```json
{
  "mcpServers": {
    "bcut-asr": {
      "command": "python",
      "args": ["-m", "bcut_asr_skill.mcp"],
      "env": {}
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `bcut_asr_transcribe` | Transcribe audio/video to subtitles |
| `bcut_tts_synthesize` | Synthesize speech from text |
| `bcut_tts_list_voices` | List available TTS voices |

## Usage

```bash
# In OpenClaw chat:
# > transcribe meeting.mp3 to srt
# > synthesize "Hello world" with dingzhen voice
```
