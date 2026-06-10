"""Pydantic v2 数据模型

定义 ASR / TTS 相关的所有请求/响应数据结构，
以及任务状态枚举和语音片段模型。
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# ASR 模型
# ---------------------------------------------------------------------------


class ResultStateEnum(int, Enum):
    """ASR 任务状态枚举"""

    STOP = 0      # 未开始
    RUNNING = 1   # 运行中
    ERROR = 3     # 错误
    COMPLETE = 4  # 完成


class ASRDataWords(BaseModel):
    """ASR 逐字识别结果"""

    label: str       # 文字内容
    start_time: int  # 开始时间 (ms)
    end_time: int    # 结束时间 (ms)


class ASRDataSeg(BaseModel):
    """ASR 断句结果"""

    start_time: int               # 开始时间 (ms)
    end_time: int                 # 结束时间 (ms)
    transcript: str               # 整句文本
    words: list[ASRDataWords] = Field(default_factory=list)

    def to_srt_ts(self) -> str:
        """转换为 SRT 时间戳格式 HH:MM:SS,mmm --> HH:MM:SS,mmm"""

        def _conv(ms: int) -> tuple[int, int, int, int]:
            return ms // 3_600_000, ms // 60_000 % 60, ms // 1_000 % 60, ms % 1_000

        s_h, s_m, s_s, s_ms = _conv(self.start_time)
        e_h, e_m, e_s, e_ms = _conv(self.end_time)
        return (
            f"{s_h:02d}:{s_m:02d}:{s_s:02d},{s_ms:03d} --> "
            f"{e_h:02d}:{e_m:02d}:{e_s:02d},{e_ms:03d}"
        )

    def to_lrc_ts(self) -> str:
        """转换为 LRC 时间戳格式 [MM:SS.mm]"""

        def _conv(ms: int) -> tuple[int, int, int]:
            return ms // 60_000, ms // 1_000 % 60, ms % 1_000 // 10

        s_m, s_s, s_ms = _conv(self.start_time)
        return f"[{s_m:02d}:{s_s:02d}.{s_ms:02d}]"


class ASRData(BaseModel):
    """ASR 完整识别结果"""

    utterances: list[ASRDataSeg] = Field(default_factory=list)
    version: str = ""

    def __iter__(self):  # type: ignore[override]
        return iter(self.utterances)

    def has_data(self) -> bool:
        """是否识别到有效数据"""
        return len(self.utterances) > 0


class ResourceCreateRspSchema(BaseModel):
    """ASR 上传申请响应"""

    resource_id: str
    title: str
    type: int
    in_boss_key: str
    size: int
    upload_urls: list[str]
    upload_id: str
    per_size: int


class ResourceCompleteRspSchema(BaseModel):
    """ASR 上传提交响应"""

    resource_id: str
    download_url: str


class TaskCreateRspSchema(BaseModel):
    """任务创建响应 (ASR / TTS 通用)"""

    resource: str = ""
    result: str = ""
    task_id: str
    poll_time: int = 0
    mark: int = 0
    timeout_time: int = 0
    state: int = 0


class ResultRspSchema(BaseModel):
    """ASR 任务结果查询响应"""

    task_id: str
    result: Optional[str] = None  # JSON 字符串，运行中可能为 None
    remark: str = ""
    state: ResultStateEnum

    def parse(self) -> ASRData:
        """解析 result 字段为 ASRData"""
        if self.result is None:
            return ASRData()
        return ASRData.model_validate_json(self.result)


# ---------------------------------------------------------------------------
# TTS 模型
# ---------------------------------------------------------------------------


class VoiceMaterial(BaseModel):
    """TTS 音色素材"""

    id: int
    name: str
    cover: str = ""
    voice: str = ""           # API 调用时使用的音色标识符
    voice_type: int = 1
    voice_engine: str = "bili-fewshot"
    pitch_rate: int = 0
    speech_rate: int = 0
    pre_volume: float = 1.0
    gen_volume: float = 1.0
    state: int = 0
    tags: str = ""
    tts_tags: str = ""
    ssml_effect: str = ""
    cat_id: int = 0
    download_url: str = ""
    preview_url: str = ""
    rank: int = 0
    biz_from: int = 0


class VoiceCategory(BaseModel):
    """TTS 音色分类"""

    id: int
    title: str
    cover: str = ""
    materials: list[VoiceMaterial] = Field(default_factory=list)
    rank: int = 0


class TTSParams(BaseModel):
    """TTS 合成参数"""

    pitch_rate: int = 0        # 音调 -300~300
    sample_rate: int = 24_000  # 采样率
    speech_rate: int = 0       # 语速 -300~300
    voice: str = "dingzhen"
    voice_engine: str = "bili-fewshot"
    volume: int = 100          # 音量 0~100


class TTSResultData(BaseModel):
    """TTS 合成结果数据"""

    audio_url: str
    meta_url: Optional[str] = None
    sep_url: Optional[str] = None


class TTSResultRspSchema(BaseModel):
    """TTS 任务结果查询响应"""

    task_id: str
    poll_time: int = 0
    result: str = ""   # JSON 字符串
    mark: int = 0
    timeout_time: int = 0
    state: int = 0
    remark: str = ""

    def is_complete(self) -> bool:
        """判断任务是否完成 (state=0 且 audio_url 非空)"""
        if self.state != 0:
            return False
        if not self.result:
            return False
        try:
            data = TTSResultData.model_validate_json(self.result)
            return bool(data.audio_url)
        except Exception:
            return False

    def parse(self) -> TTSResultData:
        """解析 result 字段为 TTSResultData"""
        return TTSResultData.model_validate_json(self.result)
