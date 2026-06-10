"""测试 ASR / TTS 数据模型 (Pydantic v2)

覆盖所有模型的创建、验证、序列化与业务方法。
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from bcut_asr_skill.models import (
    ASRData,
    ASRDataSeg,
    ASRDataWords,
    ResourceCompleteRspSchema,
    ResourceCreateRspSchema,
    ResultRspSchema,
    ResultStateEnum,
    TaskCreateRspSchema,
    TTSParams,
    TTSResultData,
    TTSResultRspSchema,
    VoiceCategory,
    VoiceMaterial,
)


# ---------------------------------------------------------------------------
# ASR 模型测试
# ---------------------------------------------------------------------------


class TestResultStateEnum:
    def test_members(self):
        assert ResultStateEnum.STOP == 0
        assert ResultStateEnum.RUNNING == 1
        assert ResultStateEnum.ERROR == 3
        assert ResultStateEnum.COMPLETE == 4


class TestASRDataWords:
    def test_create(self):
        w = ASRDataWords(label="你好", start_time=0, end_time=500)
        assert w.label == "你好"
        assert w.end_time == 500

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            ASRDataWords(label="x")  # type: ignore[call-arg]


class TestASRDataSeg:
    def test_create_with_words(self):
        seg = ASRDataSeg(
            start_time=0,
            end_time=2000,
            transcript="你好世界",
            words=[ASRDataWords(label="你好", start_time=0, end_time=800)],
        )
        assert seg.transcript == "你好世界"
        assert len(seg.words) == 1

    def test_to_srt_ts(self):
        seg = ASRDataSeg(start_time=3661001, end_time=3662002, transcript="")
        ts = seg.to_srt_ts()
        assert ts == "01:01:01,001 --> 01:01:02,002"

    def test_to_lrc_ts(self):
        seg = ASRDataSeg(start_time=65000, end_time=66000, transcript="")
        ts = seg.to_lrc_ts()
        assert ts == "[01:05.00]"


class TestASRData:
    def test_empty(self):
        data = ASRData()
        assert not data.has_data()
        assert list(data) == []

    def test_iter(self):
        seg = ASRDataSeg(start_time=0, end_time=1000, transcript="hi")
        data = ASRData(utterances=[seg])
        assert data.has_data()
        assert list(data) == [seg]

    def test_json_roundtrip(self):
        data = ASRData(
            utterances=[
                ASRDataSeg(
                    start_time=0,
                    end_time=1000,
                    transcript="test",
                    words=[ASRDataWords(label="t", start_time=0, end_time=500)],
                )
            ],
            version="v1",
        )
        raw = data.model_dump_json()
        restored = ASRData.model_validate_json(raw)
        assert restored.version == "v1"
        assert restored.utterances[0].transcript == "test"


class TestResourceCreateRspSchema:
    def test_create(self):
        rsp = ResourceCreateRspSchema(
            resource_id="r1",
            title="t",
            type=2,
            in_boss_key="bk",
            size=1024,
            upload_urls=["http://u1"],
            upload_id="uid",
            per_size=1024,
        )
        assert rsp.resource_id == "r1"


class TestResourceCompleteRspSchema:
    def test_create(self):
        rsp = ResourceCompleteRspSchema(resource_id="r1", download_url="http://d1")
        assert rsp.download_url == "http://d1"


class TestTaskCreateRspSchema:
    def test_defaults(self):
        rsp = TaskCreateRspSchema(task_id="t1")
        assert rsp.task_id == "t1"
        assert rsp.poll_time == 0


class TestResultRspSchema:
    def test_parse_with_result(self):
        asr_data = ASRData(
            utterances=[ASRDataSeg(start_time=0, end_time=1000, transcript="hello")]
        )
        rsp = ResultRspSchema(
            task_id="t1",
            result=asr_data.model_dump_json(),
            state=ResultStateEnum.COMPLETE,
        )
        parsed = rsp.parse()
        assert parsed.has_data()
        assert parsed.utterances[0].transcript == "hello"

    def test_parse_none_result(self):
        rsp = ResultRspSchema(task_id="t1", result=None, state=ResultStateEnum.RUNNING)
        parsed = rsp.parse()
        assert not parsed.has_data()


# ---------------------------------------------------------------------------
# TTS 模型测试
# ---------------------------------------------------------------------------


class TestVoiceMaterial:
    def test_defaults(self):
        vm = VoiceMaterial(id=1, name="测试音色")
        assert vm.voice == ""
        assert vm.voice_engine == "bili-fewshot"
        assert vm.pitch_rate == 0


class TestVoiceCategory:
    def test_create(self):
        vc = VoiceCategory(
            id=1,
            title="分类A",
            materials=[VoiceMaterial(id=1, name="m1")],
        )
        assert len(vc.materials) == 1


class TestTTSParams:
    def test_defaults(self):
        p = TTSParams()
        assert p.voice == "dingzhen"
        assert p.sample_rate == 24_000

    def test_custom(self):
        p = TTSParams(pitch_rate=100, speech_rate=-50, volume=80)
        assert p.pitch_rate == 100
        assert p.volume == 80


class TestTTSResultData:
    def test_create(self):
        d = TTSResultData(audio_url="http://a1")
        assert d.audio_url == "http://a1"
        assert d.meta_url is None


class TestTTSResultRspSchema:
    def test_is_complete_true(self):
        data = TTSResultData(audio_url="http://a1")
        rsp = TTSResultRspSchema(task_id="t1", result=data.model_dump_json(), state=0)
        assert rsp.is_complete()

    def test_is_complete_empty_audio(self):
        data = TTSResultData(audio_url="")
        rsp = TTSResultRspSchema(task_id="t1", result=data.model_dump_json(), state=0)
        assert not rsp.is_complete()

    def test_is_complete_error_state(self):
        rsp = TTSResultRspSchema(task_id="t1", result="", state=3)
        assert not rsp.is_complete()

    def test_parse(self):
        data = TTSResultData(audio_url="http://a1", meta_url="http://m1")
        rsp = TTSResultRspSchema(task_id="t1", result=data.model_dump_json(), state=0)
        parsed = rsp.parse()
        assert parsed.audio_url == "http://a1"
        assert parsed.meta_url == "http://m1"
