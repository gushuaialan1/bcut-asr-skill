"""测试输出格式转换器

覆盖 SRT / LRC / TXT / JSON 四种格式的生成与边界情况。
"""

from __future__ import annotations

import json

import pytest

from bcut_asr_skill.formats import OutputFormat, convert, to_json, to_lrc, to_srt, to_txt
from bcut_asr_skill.models import ASRData, ASRDataSeg


@pytest.fixture
def sample_data() -> ASRData:
    """提供包含两条 utterances 的 ASRData"""
    return ASRData(
        utterances=[
            ASRDataSeg(start_time=0, end_time=2500, transcript="第一句"),
            ASRDataSeg(start_time=3000, end_time=5500, transcript="第二句更长"),
        ]
    )


class TestToSrt:
    def test_basic(self, sample_data: ASRData):
        srt = to_srt(sample_data)
        lines = srt.strip().split("\n")
        assert lines[0] == "1"
        assert "00:00:00,000 --> 00:00:02,500" in lines[1]
        assert lines[2] == "第一句"
        assert lines[3] == ""
        assert lines[4] == "2"

    def test_empty(self):
        assert to_srt(ASRData()) == ""


class TestToLrc:
    def test_basic(self, sample_data: ASRData):
        lrc = to_lrc(sample_data)
        lines = lrc.strip().split("\n")
        assert lines[0] == "[00:00.00]第一句"
        assert lines[1] == "[00:03.00]第二句更长"

    def test_empty(self):
        assert to_lrc(ASRData()) == ""


class TestToTxt:
    def test_basic(self, sample_data: ASRData):
        txt = to_txt(sample_data)
        assert txt == "第一句\n第二句更长"

    def test_empty(self):
        assert to_txt(ASRData()) == ""


class TestToJson:
    def test_basic(self, sample_data: ASRData):
        raw = to_json(sample_data)
        obj = json.loads(raw)
        assert obj["utterances"][0]["transcript"] == "第一句"

    def test_no_indent(self, sample_data: ASRData):
        raw = to_json(sample_data, indent=None)
        assert "\n" not in raw


class TestConvert:
    def test_all_formats(self, sample_data: ASRData):
        assert " --> " in convert(sample_data, OutputFormat.SRT)
        assert "[" in convert(sample_data, OutputFormat.LRC)
        assert "第一句" in convert(sample_data, OutputFormat.TXT)
        assert "utterances" in convert(sample_data, OutputFormat.JSON)

    def test_invalid_format(self, sample_data: ASRData):
        with pytest.raises(ValueError, match="不支持的输出格式"):
            convert(sample_data, "xyz")  # type: ignore[arg-type]
