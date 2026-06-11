"""音色数据管理 — 本地 JSON 缓存 + 在线更新"""

import json
import logging
from pathlib import Path
from typing import Optional

import importlib.resources as res

from .models import VoiceCategory, VoiceMaterial

logger = logging.getLogger(__name__)


def _get_data_path() -> Path:
    """获取用户可写的音色数据文件路径 (~/.bcut/voices.json)"""
    return Path.home() / ".bcut" / "voices.json"


def _get_builtin_path() -> Path:
    """获取包内自带的音色数据文件路径"""
    return res.files("bcut_asr_skill") / "data" / "voices.json"


def load_voice_data() -> Optional[list[VoiceCategory]]:
    """加载音色数据：优先用户缓存，其次包内默认"""
    user_path = _get_data_path()
    if user_path.exists():
        try:
            with open(user_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return [_parse_category(c) for c in raw]
        except Exception as e:
            logger.warning(f"用户音色缓存损坏，使用内置默认: {e}")

    # 使用包内默认
    try:
        builtin = _get_builtin_path()
        with builtin.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return [_parse_category(c) for c in raw]
    except Exception as e:
        logger.warning(f"内置音色数据加载失败: {e}")
        return None


def save_voice_data(categories: list[VoiceCategory]) -> None:
    """保存音色数据到用户缓存目录"""
    path = _get_data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = []
    for cat in categories:
        cat_data = {
            "id": cat.id,
            "title": cat.title,
            "cover": cat.cover,
            "rank": cat.rank,
            "materials": [
                {
                    "id": m.id,
                    "name": m.name,
                    "voice": m.voice,
                    "voice_engine": m.voice_engine,
                    "tts_tags": m.tts_tags,
                    "ssml_effect": m.ssml_effect,
                }
                for m in cat.materials
            ],
        }
        data.append(cat_data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"音色数据已保存: {path}")


def _parse_category(raw: dict) -> VoiceCategory:
    """将 JSON dict 解析为 VoiceCategory"""
    materials = [
        VoiceMaterial(
            id=m["id"],
            name=m["name"],
            voice=m["voice"],
            voice_engine=m.get("voice_engine", "bili-fewshot"),
            tts_tags=m.get("tts_tags", ""),
            ssml_effect=m.get("ssml_effect", ""),
        )
        for m in raw.get("materials", [])
    ]
    return VoiceCategory(
        id=raw["id"],
        title=raw["title"],
        cover=raw.get("cover", ""),
        materials=materials,
        rank=raw.get("rank", 0),
    )
