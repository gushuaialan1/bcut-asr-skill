"""工具函数

文件读取、ffmpeg 音频提取、路径处理等辅助功能。
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Literal

from .exceptions import FFmpegError

logger = logging.getLogger(__name__)

# 支持的音频格式
SUPPORT_SOUND_FORMAT = Literal["flac", "aac", "m4a", "mp3", "wav"]
AUDIO_EXTS: set[str] = {"flac", "aac", "m4a", "mp3", "wav"}


def read_media_file(file_path: str | Path) -> tuple[bytes, str]:
    """读取媒体文件，返回 (二进制数据, 格式后缀)

    如果是视频文件，自动调用 ffmpeg 提取音频为 aac 格式。
    """
    path = Path(file_path)
    suffix = path.suffix.lstrip(".").lower()

    if suffix in AUDIO_EXTS:
        return path.read_bytes(), suffix

    # 视频文件：尝试 ffmpeg 提取伴音
    logger.info("非标准音频文件，尝试调用 ffmpeg 转码")
    audio_bytes = ffmpeg_extract_audio(str(path))
    logger.info("ffmpeg 转码完成")
    return audio_bytes, "aac"


def ffmpeg_extract_audio(media_file: str) -> bytes:
    """使用 ffmpeg 提取视频伴音并转码为 aac (adts) 格式"""
    cmd = [
        "ffmpeg",
        "-v", "warning",
        "-i", media_file,
        "-ac", "1",
        "-f", "adts",
        "pipe:1",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise FFmpegError(f"ffmpeg 转码失败: {exc.stderr.decode('utf-8', errors='ignore')}")
    except FileNotFoundError:
        raise FFmpegError("未找到 ffmpeg，请确保已安装并加入 PATH")
    return result.stdout


def guess_output_format(file_path: str | Path | None, fallback: str = "srt") -> str:
    """从输出文件路径推断格式，无路径时返回 fallback"""
    if file_path is None:
        return fallback
    suffix = Path(file_path).suffix.lstrip(".").lower()
    if suffix in {"srt", "lrc", "txt", "json"}:
        return suffix
    return fallback
