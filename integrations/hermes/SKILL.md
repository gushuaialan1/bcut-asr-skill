---
name: bcut-asr-skill
description: Bilibili BCut ASR & TTS skill for Hermes Agent. Provides speech recognition and synthesis capabilities.
version: 1.0.0
---

# BCut ASR Skill for Hermes

Bilibili 必剪云端语音服务的 Hermes Skill，提供 ASR 语音识别和 TTS 语音合成能力。

## 依赖

```bash
pip install bcut-asr-skill
```

## 工具

### `bcut_asr_transcribe`

语音识别：将音频/视频转录为字幕。

```yaml
tool: bcut_asr_transcribe
args:
  file_path: "/path/to/audio.mp3"
  output_format: "srt"  # srt | lrc | txt | json
  output_path: "/path/to/output.srt"  # optional
```

### `bcut_tts_synthesize`

语音合成：将文本合成为语音。

```yaml
tool: bcut_tts_synthesize
args:
  text: "你好，世界"
  output_path: "/path/to/output.wav"
  voice: "dingzhen"
  pitch: 0
  speed: 0
  volume: 100
```

### `bcut_tts_list_voices`

列出所有可用音色。

```yaml
tool: bcut_tts_list_voices
args: {}
```

## 使用示例

```python
from bcut_asr_skill import BCutASRClient, BCutTTSClient, OutputFormat

# ASR
client = BCutASRClient()
srt = client.transcribe("meeting.mp3", output_format=OutputFormat.SRT)

# TTS
client = BCutTTSClient()
client.synthesize("欢迎使用", "welcome.wav", voice="dingzhen")
```

## 安装到 Hermes

```bash
# 复制到 Hermes skills 目录
cp -r integrations/hermes ~/.hermes/skills/media/bcut-asr-skill

# 或直接引用
hermes skill add bcut-asr-skill --from-github gushuaialan1/bcut-asr-skill
```
