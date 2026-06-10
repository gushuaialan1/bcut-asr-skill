# BCut ASR Skill API 文档

## 概述

`bcut-asr-skill` 是基于 Pydantic v2 + `httpx`/`requests` 构建的必剪语音识别 (ASR) 与语音合成 (TTS) 现代 Python 库，提供同步与异步两套 API。

---

## 安装

```bash
pip install bcut-asr-skill
```

开发依赖：

```bash
pip install -e ".[dev]"
```

---

## 快速开始

### 语音识别 (ASR)

```python
from bcut_asr_skill import BCutASRClient, OutputFormat

client = BCutASRClient()
srt = client.transcribe("audio.mp3", output_format=OutputFormat.SRT)
print(srt)
```

### 语音合成 (TTS)

```python
from bcut_asr_skill import BCutTTSClient

client = BCutTTSClient()
client.synthesize("你好，世界", "output.wav", voice="dingzhen")
```

### 异步用法

```python
import asyncio
from bcut_asr_skill import AsyncBCutASRClient, OutputFormat

async def main():
    async with AsyncBCutASRClient() as client:
        srt = await client.transcribe("audio.mp3", output_format=OutputFormat.SRT)
        print(srt)

asyncio.run(main())
```

---

## ASR 客户端

### `BCutASRClient`

同步语音识别客户端。

#### 构造函数

```python
BCutASRClient(session: requests.Session | None = None)
```

- `session`: 自定义 `requests.Session`，用于复用连接池或注入代理。

#### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `upload` | `upload(sound_name, sound_bin, sound_fmt) -> str` | 上传音频，返回下载 URL |
| `create_task` | `create_task(download_url) -> str` | 创建识别任务，返回 `task_id` |
| `query_result` | `query_result(task_id=None) -> ResultRspSchema` | 查询任务结果 |
| `transcribe` | `transcribe(file_path, *, output_format=SRT, poll_interval=1.0, timeout=300.0) -> str` | 一站式识别 |

#### `transcribe` 参数

- `file_path`: 输入媒体文件路径（支持视频，自动调用 ffmpeg 提取伴音）
- `output_format`: 输出格式 (`OutputFormat.SRT` / `.LRC` / `.TXT` / `.JSON`)
- `poll_interval`: 轮询间隔（秒）
- `timeout`: 总超时（秒）

---

### `AsyncBCutASRClient`

异步语音识别客户端，基于 `httpx.AsyncClient`。

#### 构造函数

```python
AsyncBCutASRClient(client: httpx.AsyncClient | None = None)
```

支持异步上下文管理器 (`async with`) 自动关闭连接。

---

## TTS 客户端

### `BCutTTSClient`

同步语音合成客户端。

#### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `list_voices` | `list_voices(force_refresh=False) -> list[VoiceCategory]` | 获取可用音色列表 |
| `find_voice` | `find_voice(name) -> VoiceMaterial \| None` | 按名称或 voice 值查找音色 |
| `create_task` | `create_task(text, voice="dingzhen", pitch=0, speed=0, volume=100) -> str` | 创建合成任务 |
| `query_result` | `query_result(task_id) -> TTSResultRspSchema` | 查询任务结果 |
| `synthesize` | `synthesize(text, output_path, *, voice="dingzhen", ...) -> str` | 一站式合成并下载 |

---

### `AsyncBCutTTSClient`

异步语音合成客户端。

---

## 数据模型

### ASR 相关

| 模型 | 说明 |
|------|------|
| `ASRData` | 完整识别结果，包含 `utterances: list[ASRDataSeg]` |
| `ASRDataSeg` | 单句识别结果，含时间戳与逐字信息 |
| `ASRDataWords` | 逐字识别结果 |
| `ResultRspSchema` | 任务查询响应，`parse()` 可解析为 `ASRData` |
| `ResultStateEnum` | 任务状态：`STOP=0`, `RUNNING=1`, `ERROR=3`, `COMPLETE=4` |

### TTS 相关

| 模型 | 说明 |
|------|------|
| `VoiceCategory` | 音色分类 |
| `VoiceMaterial` | 单条音色素材 |
| `TTSResultData` | 合成结果，含 `audio_url` |
| `TTSResultRspSchema` | 任务查询响应，`is_complete()` / `parse()` |

---

## 输出格式

```python
from bcut_asr_skill import OutputFormat, convert

# 四种格式
OutputFormat.SRT   # SRT 字幕
OutputFormat.LRC   # LRC 歌词
OutputFormat.TXT   # 纯文本
OutputFormat.JSON  # JSON 原始数据

# 手动转换
from bcut_asr_skill import to_srt, to_lrc, to_txt, to_json
srt = to_srt(asr_data)
```

---

## 异常处理

```python
from bcut_asr_skill import BCutError, APIError, TaskTimeoutError, FFmpegError

try:
    client.transcribe("video.mp4")
except APIError as e:
    print(f"API 错误: {e.code} - {e.msg}")
except TaskTimeoutError:
    print("任务超时")
except FFmpegError:
    print("ffmpeg 未安装或转码失败")
```

| 异常 | 说明 |
|------|------|
| `BCutError` | 基类异常 |
| `APIError` | B站 API 返回业务错误 |
| `TaskTimeoutError` | 轮询超时 |
| `FFmpegError` | ffmpeg 调用失败 |
| `FormatError` | 格式转换错误 |

---

## CLI 用法

```bash
# 语音识别
bcut-asr input.mp3 -o output.srt
bcut-asr input.mp4 -f json -t 600

# 语音合成
bcut-tts "你好世界" -o hello.wav -v dingzhen
bcut-tts -l                    # 列出所有音色
```

---

## 测试

```bash
pytest -v
```

测试使用 `unittest.mock` 模拟所有 HTTP 请求，无需真实网络环境。
