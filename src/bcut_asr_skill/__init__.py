"""BCut ASR Skill - 必剪语音识别与语音合成现代 Python 库

基于 Pydantic v2 + httpx(async) / requests(sync) 构建，
提供简洁的同步与异步 API。

示例::

    from bcut_asr_skill import BCutASRClient, OutputFormat

    client = BCutASRClient()
    srt = client.transcribe("audio.mp3", output_format=OutputFormat.SRT)

    # 异步
    import asyncio
    from bcut_asr_skill import AsyncBCutASRClient

    async def main():
        async with AsyncBCutASRClient() as client:
            srt = await client.transcribe("audio.mp3")
            print(srt)

    asyncio.run(main())
"""

from __future__ import annotations

from .client import (
    AsyncBCutASRClient,
    AsyncBCutTTSClient,
    BCutASRClient,
    BCutTTSClient,
)
from .exceptions import APIError, BCutError, FFmpegError, FormatError, TaskTimeoutError
from .formats import OutputFormat, convert, to_json, to_lrc, to_srt, to_txt
from .models import (
    ASRData,
    ASRDataSeg,
    ASRDataWords,
    ResultRspSchema,
    ResultStateEnum,
    TTSResultData,
    VoiceCategory,
    VoiceMaterial,
)

__version__ = "0.1.0"

__all__ = [
    # 客户端
    "BCutASRClient",
    "BCutTTSClient",
    "AsyncBCutASRClient",
    "AsyncBCutTTSClient",
    # 异常
    "BCutError",
    "APIError",
    "FFmpegError",
    "FormatError",
    "TaskTimeoutError",
    # 格式
    "OutputFormat",
    "convert",
    "to_srt",
    "to_lrc",
    "to_txt",
    "to_json",
    # 模型
    "ASRData",
    "ASRDataSeg",
    "ASRDataWords",
    "ResultRspSchema",
    "ResultStateEnum",
    "TTSResultData",
    "VoiceCategory",
    "VoiceMaterial",
]
