---
name: bcut-asr
description: Bilibili BCut ASR & TTS skill. Provides speech-to-text (ASR) transcription and text-to-speech (TTS) synthesis with 100+ voices, supporting SRT/LRC/TXT/JSON output formats.
version: 1.0.0
---

# BCut ASR Skill

Bilibili 必剪云端语音服务的 AI Agent Skill，提供 ASR 语音识别和 TTS 语音合成能力。

## 安装

```bash
pip install bcut-asr-skill
```

## 可用工具

| 工具名 | 功能 |
|--------|------|
| `bcut_asr_transcribe` | 将音频/视频转录为字幕 |
| `bcut_tts_synthesize` | 将文本合成为语音 |
| `bcut_tts_list_voices` | 列出所有可用音色 |

---

### `bcut_asr_transcribe`

语音识别：将音频/视频文件转录为字幕文本。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file_path` | string | ✅ | - | 音频或视频文件路径。支持 mp3, wav, flac, aac, m4a, mp4（自动 ffmpeg 提取音频） |
| `output_format` | string | ❌ | `srt` | 输出格式：`srt` \| `lrc` \| `txt` \| `json` |
| `output_path` | string | ❌ | - | 可选的输出文件路径。不提供则直接返回文本 |

**示例：**

```yaml
tool: bcut_asr_transcribe
args:
  file_path: "/path/to/meeting.mp3"
  output_format: "srt"
```

---

### `bcut_tts_synthesize`

语音合成：将文本合成为语音文件。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | ✅ | - | 要合成的文本（推荐中文） |
| `output_path` | string | ✅ | - | 输出 WAV 文件路径 |
| `voice` | string | ❌ | `dingzhen` | 音色标识。使用 `bcut_tts_list_voices` 查看所有选项 |
| `pitch` | integer | ❌ | `0` | 音调调整，范围 `-300` ~ `300` |
| `speed` | integer | ❌ | `0` | 语速调整，范围 `-300` ~ `300` |
| `volume` | integer | ❌ | `100` | 音量大小，范围 `0` ~ `100` |

**示例：**

```yaml
tool: bcut_tts_synthesize
args:
  text: "欢迎使用必剪语音合成服务"
  output_path: "/path/to/output.wav"
  voice: "dingzhen"
  pitch: 0
  speed: 0
  volume: 100
```

---

### `bcut_tts_list_voices`

列出所有可用的 TTS 音色，包含分类和元数据。

**参数：** 无

**示例：**

```yaml
tool: bcut_tts_list_voices
args: {}
```

---

## 各平台集成

### Hermes Agent

Hermes 会自动识别 `SKILL.md` 中的工具定义并注册为可用工具。

安装方式：

```bash
# 通过 npx skills 安装（推荐）
npx skills add gushuaialan1/bcut-asr-skill

# 或手动复制到 skills 目录
cp -r skills/bcut-asr ~/.hermes/skills/
```

### Claude Code

将以下 JSON 工具定义添加到 Claude Code agent 的 `tools` 配置中：

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

Python handler 示例：

```python
from bcut_asr_skill import BCutASRClient, BCutTTSClient, OutputFormat

def bcut_asr_transcribe(file_path: str, output_format: str = "srt", output_path: str = None):
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
    client = BCutTTSClient()
    path = client.synthesize(text, output_path, voice=voice,
                             pitch=pitch, speed=speed, volume=volume)
    return {"status": "success", "output_path": path}

def bcut_tts_list_voices():
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

### OpenClaw / MCP 兼容客户端

在 `mcpServers` 配置中添加：

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

启动后客户端可通过 MCP 协议调用上述三个工具。

### Codex / 其他 Agent

本 Skill 提供标准的 MCP server（`python -m bcut_asr_skill.mcp`），任何支持 MCP 的 Agent 均可直接接入。

---

## Python SDK 直接使用

```python
from bcut_asr_skill import BCutASRClient, BCutTTSClient, OutputFormat

# ASR 语音识别
client = BCutASRClient()
srt = client.transcribe("meeting.mp3", output_format=OutputFormat.SRT)

# TTS 语音合成
client = BCutTTSClient()
client.synthesize("欢迎使用", "welcome.wav", voice="dingzhen")

# 异步支持
import asyncio
from bcut_asr_skill import AsyncBCutASRClient

async def main():
    async with AsyncBCutASRClient() as client:
        srt = await client.transcribe("audio.mp3")
        print(srt)

asyncio.run(main())
```

---

## 依赖

- Python >= 3.10
- `pydantic>=2.0`
- `httpx>=0.27`
- `requests>=2.31`
- `ffmpeg`（用于视频文件音频提取，可选）
