"""输出格式转换器

将 ASRData 转换为 SRT / LRC / TXT / JSON 等常见字幕/文本格式。
"""

from __future__ import annotations

import json
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ASRData, ASRDataSeg


class OutputFormat(str, Enum):
    """支持的输出格式枚举"""

    SRT = "srt"
    LRC = "lrc"
    TXT = "txt"
    JSON = "json"


def to_srt(data: ASRData) -> str:
    """ASRData → SRT 字幕格式"""
    lines: list[str] = []
    for n, seg in enumerate(data.utterances, 1):
        lines.append(f"{n}\n{seg.to_srt_ts()}\n{seg.transcript}\n")
    return "\n".join(lines)


def to_lrc(data: ASRData) -> str:
    """ASRData → LRC 歌词格式"""
    return "\n".join(
        f"{seg.to_lrc_ts()}{seg.transcript}" for seg in data.utterances
    )


def to_txt(data: ASRData) -> str:
    """ASRData → 纯文本 (无时间戳)"""
    return "\n".join(seg.transcript for seg in data.utterances)


def to_json(data: ASRData, *, indent: int | None = 2) -> str:
    """ASRData → JSON 字符串"""
    return data.model_dump_json(indent=indent)


def convert(data: ASRData, fmt: OutputFormat) -> str:
    """根据格式枚举统一调度转换"""
    match fmt:
        case OutputFormat.SRT:
            return to_srt(data)
        case OutputFormat.LRC:
            return to_lrc(data)
        case OutputFormat.TXT:
            return to_txt(data)
        case OutputFormat.JSON:
            return to_json(data)
        case _:
            raise ValueError(f"不支持的输出格式: {fmt}")
