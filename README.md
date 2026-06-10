<div align="center">

# bcut-asr-skill

**Modern Python SDK + Universal Agent Skill for Bilibili BCut ASR & TTS**

[![CI](https://github.com/gushuaialan1/bcut-asr-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/gushuaialan1/bcut-asr-skill/actions)
[![PyPI](https://img.shields.io/pypi/v/bcut-asr-skill)](https://pypi.org/project/bcut-asr-skill/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[English](#english) | [中文](#中文)

</div>

---

<a name="english"></a>
## English

> A clean, modern Python SDK for Bilibili's "Bijian" (BCut) cloud speech services — ASR (Automatic Speech Recognition) and TTS (Text-to-Speech). Built for agents, developers, and automation pipelines.
>
> **One-line install as an Agent Skill:**
> ```bash
> npx skills add https://github.com/gushuaialan1/bcut-asr-skill
> ```

### Features

- **ASR** — Transcribe audio/video to SRT / LRC / TXT / JSON subtitles
- **TTS** — Synthesize speech with 100+ voices (Bili-fewshot + MiniMax engines)
- **Async-first** — Built on `httpx` with full async/await support
- **Sync fallback** — `requests`-based synchronous clients for simple scripts
- **Type-safe** — Pydantic v2 models with full type annotations
- **Agent-friendly** — Clean API, small files, easy to embed in AI agent workflows
- **CLI included** — `bcut-asr` and `bcut-tts` command-line tools

### Quick Start

```bash
# 注意：PyPI 包尚未发布，请使用源码安装
pip install git+https://github.com/gushuaialan1/bcut-asr-skill.git
```

#### ASR — Transcribe Audio

```python
from bcut_asr_skill import BCutASRClient

client = BCutASRClient()
result = client.transcribe("audio.mp3")
print(result.to_srt())
```

#### TTS — Synthesize Speech

```python
from bcut_asr_skill import BCutTTSClient

client = BCutTTSClient()
client.synthesize(
    text="Hello, world!",
    output_path="output.wav",
    voice="dingzhen",
)
```

#### Async Usage

```python
import asyncio
from bcut_asr_skill import AsyncBCutASRClient

async def main():
    async with AsyncBCutASRClient() as client:
        result = await client.transcribe("audio.mp3")
        print(result.to_srt())

asyncio.run(main())
```

### CLI

```bash
# ASR: transcribe audio to SRT
bcut-asr audio.mp3 -f srt -o subtitle.srt

# TTS: list voices
bcut-tts -l

# TTS: synthesize with specific voice
bcut-tts "Hello world" -v dingzhen -o hello.wav
```

### Architecture

| Module | Purpose | Lines |
|--------|---------|-------|
| `client.py` | Sync + Async clients for ASR & TTS | ~600 |
| `models.py` | Pydantic v2 data models | ~210 |
| `formats.py` | SRT / LRC / TXT / JSON converters | ~60 |
| `exceptions.py` | Custom exception hierarchy | ~40 |
| `utils.py` | File I/O, ffmpeg helpers | ~70 |
| `cli.py` | argparse CLI entry points | ~160 |

### Installation

```bash
# 注意：PyPI 包尚未发布，请使用源码安装
pip install git+https://github.com/gushuaialan1/bcut-asr-skill.git

# As an Agent Skill (supports Claude Code / Cursor / Hermes / Windsurf / Codex / etc.)
npx skills add https://github.com/gushuaialan1/bcut-asr-skill

# From source
git clone https://github.com/gushuaialan1/bcut-asr-skill.git
cd bcut-asr-skill
pip install -e ".[dev]"
```

### Development

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check src/
ruff format src/

# Type check
mypy src/bcut_asr_skill
```

### Tech Stack

| Component | Choice |
|-----------|--------|
| HTTP (async) | `httpx` |
| HTTP (sync) | `requests` |
| Data models | `pydantic` v2 |
| Testing | `pytest` + `pytest-asyncio` |
| Linting | `ruff` |
| Build | `setuptools` + `pyproject.toml` |

---

<a name="中文"></a>
## 中文

> 必剪（Bilibili BCut）云端语音服务的现代化 Python SDK —— 支持 ASR 语音识别和 TTS 语音合成。为 AI Agent、开发者和自动化流程设计。
>
> **一行代码安装为 Agent Skill：**
> ```bash
> npx skills add https://github.com/gushuaialan1/bcut-asr-skill
> ```

### 功能特性

- **ASR 语音识别** — 音频/视频转录为 SRT / LRC / TXT / JSON 字幕
- **TTS 语音合成** — 100+ 音色可选（B站自研 + MiniMax 引擎）
- **异步优先** — 基于 `httpx`，完整支持 async/await
- **同步兼容** — 基于 `requests` 的同步客户端，适合简单脚本
- **类型安全** — Pydantic v2 模型，完整类型注解
- **Agent 友好** — 简洁 API、小文件、易于嵌入 AI Agent 工作流
- **内置 CLI** — `bcut-asr` 和 `bcut-tts` 命令行工具

### 快速开始

```bash
# 注意：PyPI 包尚未发布，请使用源码安装
pip install git+https://github.com/gushuaialan1/bcut-asr-skill.git
```

#### ASR — 语音识别

```python
from bcut_asr_skill import BCutASRClient

client = BCutASRClient()
result = client.transcribe("audio.mp3")
print(result.to_srt())
```

#### TTS — 语音合成

```python
from bcut_asr_skill import BCutTTSClient

client = BCutTTSClient()
client.synthesize(
    text="你好，世界！",
    output_path="output.wav",
    voice="dingzhen",
)
```

#### 异步用法

```python
import asyncio
from bcut_asr_skill import AsyncBCutASRClient

async def main():
    async with AsyncBCutASRClient() as client:
        result = await client.transcribe("audio.mp3")
        print(result.to_srt())

asyncio.run(main())
```

### 命令行工具

```bash
# ASR: 音频转录为 SRT 字幕
bcut-asr audio.mp3 -f srt -o subtitle.srt

# TTS: 列出所有可用音色
bcut-tts -l

# TTS: 使用指定音色合成
bcut-tts "你好世界" -v dingzhen -o hello.wav
```

### 技术架构

| 模块 | 职责 | 行数 |
|------|------|------|
| `client.py` | ASR & TTS 同步/异步客户端 | ~600 |
| `models.py` | Pydantic v2 数据模型 | ~210 |
| `formats.py` | SRT / LRC / TXT / JSON 转换器 | ~60 |
| `exceptions.py` | 自定义异常层级 | ~40 |
| `utils.py` | 文件 I/O、ffmpeg 辅助 | ~70 |
| `cli.py` | argparse CLI 入口 | ~160 |

### 安装

```bash
# 注意：PyPI 包尚未发布，请使用源码安装
pip install git+https://github.com/gushuaialan1/bcut-asr-skill.git

# 作为 Agent Skill 安装（支持 Claude Code / Cursor / Hermes / Windsurf 等）
npx skills add https://github.com/gushuaialan1/bcut-asr-skill

# 从源码安装
git clone https://github.com/gushuaialan1/bcut-asr-skill.git
cd bcut-asr-skill
pip install -e ".[dev]"
```

### 开发指南

```bash
# 运行测试
pytest tests/ -v

# 代码检查
ruff check src/
ruff format src/

# 类型检查
mypy src/bcut_asr_skill
```

### 技术栈

| 组件 | 选择 |
|------|------|
| HTTP (异步) | `httpx` |
| HTTP (同步) | `requests` |
| 数据模型 | `pydantic` v2 |
| 测试 | `pytest` + `pytest-asyncio` |
| 代码检查 | `ruff` |
| 构建 | `setuptools` + `pyproject.toml` |

---

## Roadmap

- [ ] Publish to PyPI
- [x] One-line skill install via `npx skills add`
- [ ] Add ASS subtitle format support
- [ ] Batch transcription API
- [ ] Voice cloning integration
- [ ] WebSocket real-time ASR

## Docs & Examples

- [API Documentation](docs/api.md)
- [BCut ASR Original Project](https://github.com/SocialSisterYi/bcut-asr)
- [Bilibili API Collection](https://github.com/gushuaialan1/bilibili-API-collect)

## License

MIT License — see [LICENSE](LICENSE) file.

## Credits

- Original ASR implementation: [SocialSisterYi/bcut-asr](https://github.com/SocialSisterYi/bcut-asr)
- TTS implementation based on Bilibili BCut API
- Skill design by [gushuaialan1](https://github.com/gushuaialan1)
