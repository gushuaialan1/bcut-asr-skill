"""测试同步 / 异步 HTTP 客户端

使用 unittest.mock 完全模拟 requests / httpx 的响应，
不发出任何真实网络请求。
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bcut_asr_skill.client import (
    API_COMMIT_UPLOAD,
    API_CREATE_TASK,
    API_QUERY_RESULT,
    API_REQ_UPLOAD,
    API_TTS_RESULT,
    API_TTS_TASK,
    API_TTS_VOICES,
    AsyncBCutASRClient,
    AsyncBCutTTSClient,
    BCutASRClient,
    BCutTTSClient,
)
from bcut_asr_skill.exceptions import APIError, TaskTimeoutError
from bcut_asr_skill.formats import OutputFormat
from bcut_asr_skill.models import (
    ASRData,
    ASRDataSeg,
    ResultStateEnum,
    TTSResultData,
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _json_resp(data: dict, status: int = 200) -> MagicMock:
    """构造模拟 JSON 响应对象"""
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = {"code": 0, "data": data, "message": "ok"}
    mock.headers = {"Etag": '"abc123"'}
    mock.raise_for_status.return_value = None
    return mock


def _async_json_resp(data: dict, status: int = 200):
    """构造模拟异步 JSON 响应对象 (可被 await)"""
    mock = AsyncMock()
    mock.status_code = status
    mock.json.return_value = {"code": 0, "data": data, "message": "ok"}
    mock.headers = {"Etag": '"abc123"'}
    mock.raise_for_status.return_value = None
    return mock


def _api_err(code: int = -1, msg: str = "fail") -> MagicMock:
    """构造模拟 API 错误响应"""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"code": code, "message": msg, "data": None}
    mock.raise_for_status.return_value = None
    return mock


# ---------------------------------------------------------------------------
# 同步 ASR 客户端测试
# ---------------------------------------------------------------------------


class TestBCutASRClient:
    def test_upload_success(self):
        session = MagicMock()
        session.headers = {}
        session.post.side_effect = [
            _json_resp(
                {
                    "resource_id": "r1",
                    "title": "a.mp3",
                    "type": 2,
                    "in_boss_key": "bk",
                    "size": 10,
                    "upload_urls": ["http://up"],
                    "upload_id": "uid",
                    "per_size": 10,
                }
            ),
            _json_resp({"resource_id": "r1", "download_url": "http://dl"}),
        ]
        session.put.return_value = _json_resp({})

        client = BCutASRClient(session=session)
        url = client.upload("a.mp3", b"0123456789", "mp3")
        assert url == "http://dl"
        assert session.post.call_count == 2
        assert session.put.call_count == 1

    def test_create_task(self):
        session = MagicMock()
        session.headers = {}
        session.post.return_value = _json_resp(
            {"task_id": "t1", "poll_time": 1, "result": "", "mark": 0}
        )

        client = BCutASRClient(session=session)
        tid = client.create_task("http://dl")
        assert tid == "t1"
        assert client._task_id == "t1"

    def test_query_result(self):
        asr_json = ASRData(
            utterances=[ASRDataSeg(start_time=0, end_time=1000, transcript="hi")]
        ).model_dump_json()
        session = MagicMock()
        session.headers = {}
        session.get.return_value = _json_resp(
            {"task_id": "t1", "result": asr_json, "state": 4, "remark": ""}
        )

        client = BCutASRClient(session=session)
        result = client.query_result("t1")
        assert result.state == ResultStateEnum.COMPLETE
        assert result.parse().has_data()

    @patch("bcut_asr_skill.client.read_media_file", return_value=(b"audio", "mp3"))
    @patch("bcut_asr_skill.client.time.time")
    def test_transcribe_success(self, mock_time, mock_read):
        mock_time.side_effect = [0, 0.5, 1.0, 1.5]

        asr_json = ASRData(
            utterances=[ASRDataSeg(start_time=0, end_time=1000, transcript="hello")]
        ).model_dump_json()

        session = MagicMock()
        session.headers = {}
        session.post.side_effect = [
            _json_resp(
                {
                    "resource_id": "r1",
                    "title": "x.mp3",
                    "type": 2,
                    "in_boss_key": "bk",
                    "size": 5,
                    "upload_urls": ["http://up"],
                    "upload_id": "uid",
                    "per_size": 5,
                }
            ),
            _json_resp({"resource_id": "r1", "download_url": "http://dl"}),
            _json_resp({"task_id": "t1"}),
        ]
        session.put.return_value = _json_resp({})
        session.get.return_value = _json_resp(
            {"task_id": "t1", "result": asr_json, "state": 4, "remark": ""}
        )

        client = BCutASRClient(session=session)
        out = client.transcribe("x.mp3", output_format=OutputFormat.TXT, timeout=5.0)
        assert out == "hello"

    @patch("bcut_asr_skill.client.read_media_file", return_value=(b"audio", "mp3"))
    @patch("bcut_asr_skill.client.time.time")
    def test_transcribe_api_error(self, mock_time, mock_read):
        mock_time.side_effect = [0, 0.5]

        session = MagicMock()
        session.headers = {}
        session.post.side_effect = [
            _json_resp(
                {
                    "resource_id": "r1",
                    "title": "x.mp3",
                    "type": 2,
                    "in_boss_key": "bk",
                    "size": 5,
                    "upload_urls": ["http://up"],
                    "upload_id": "uid",
                    "per_size": 5,
                }
            ),
            _json_resp({"resource_id": "r1", "download_url": "http://dl"}),
            _json_resp({"task_id": "t1"}),
        ]
        session.put.return_value = _json_resp({})
        session.get.return_value = _json_resp(
            {"task_id": "t1", "result": None, "state": 3, "remark": "识别失败"}
        )

        client = BCutASRClient(session=session)
        with pytest.raises(APIError, match="识别失败"):
            client.transcribe("x.mp3", timeout=5.0)

    @patch("bcut_asr_skill.client.read_media_file", return_value=(b"audio", "mp3"))
    @patch("bcut_asr_skill.client.time.time")
    def test_transcribe_timeout(self, mock_time, mock_read):
        mock_time.side_effect = [0, 10, 20]

        session = MagicMock()
        session.headers = {}
        session.post.side_effect = [
            _json_resp(
                {
                    "resource_id": "r1",
                    "title": "x.mp3",
                    "type": 2,
                    "in_boss_key": "bk",
                    "size": 5,
                    "upload_urls": ["http://up"],
                    "upload_id": "uid",
                    "per_size": 5,
                }
            ),
            _json_resp({"resource_id": "r1", "download_url": "http://dl"}),
            _json_resp({"task_id": "t1"}),
        ]
        session.put.return_value = _json_resp({})
        session.get.return_value = _json_resp(
            {"task_id": "t1", "result": None, "state": 1, "remark": "running"}
        )

        client = BCutASRClient(session=session)
        with pytest.raises(TaskTimeoutError):
            client.transcribe("x.mp3", timeout=5.0)

    def test_api_error_response(self):
        session = MagicMock()
        session.headers = {}
        session.post.return_value = _api_err(-1, "参数错误")

        client = BCutASRClient(session=session)
        with pytest.raises(APIError, match="参数错误"):
            client.upload("a.mp3", b"x", "mp3")

    def test_api_error_raw_response(self):
        """测试 APIError 包含 raw_response"""
        raw = {"code": -1, "message": "参数错误", "data": None}
        err = APIError(-1, "参数错误", raw_response=raw)
        assert err.code == -1
        assert err.msg == "参数错误"
        assert err.raw_response == raw

        # 不传 raw_response 时默认为 None
        err2 = APIError(500, "服务器错误")
        assert err2.raw_response is None


# ---------------------------------------------------------------------------
# 同步 TTS 客户端测试
# ---------------------------------------------------------------------------


class TestBCutTTSClient:
    def test_list_voices(self):
        session = MagicMock()
        session.headers = {}
        session.get.return_value = _json_resp(
            {
                "categories": [
                    {
                        "id": 1,
                        "title": "热门",
                        "materials": [
                            {
                                "id": 10,
                                "name": "丁真",
                                "voice": "dingzhen",
                                "extra": '{"ssml_effect": "echo"}',
                            }
                        ],
                    }
                ]
            }
        )

        client = BCutTTSClient(session=session)
        cats = client.list_voices()
        assert len(cats) == 1
        assert cats[0].materials[0].voice == "dingzhen"
        assert cats[0].materials[0].ssml_effect == "echo"

    def test_list_voices_cache_ttl(self):
        """测试 list_voices 缓存命中和过期"""
        session = MagicMock()
        session.headers = {}
        session.get.return_value = _json_resp(
            {
                "categories": [
                    {
                        "id": 1,
                        "title": "热门",
                        "materials": [{"id": 10, "name": "丁真", "voice": "dingzhen"}],
                    }
                ]
            }
        )

        with patch("bcut_asr_skill.client.time.time") as mock_time:
            client = BCutTTSClient(session=session, cache_ttl=60.0)
            # 首次调用
            mock_time.return_value = 0.0
            cats1 = client.list_voices()
            assert cats1[0].materials[0].name == "丁真"
            assert session.get.call_count == 1

            # 缓存命中（未过期）
            mock_time.return_value = 30.0
            cats2 = client.list_voices()
            assert cats2[0].materials[0].name == "丁真"
            assert session.get.call_count == 1  # 未发请求

            # 缓存过期
            mock_time.return_value = 70.0
            cats3 = client.list_voices()
            assert cats3[0].materials[0].name == "丁真"
            assert session.get.call_count == 2  # 重新请求

            # force_refresh 强制刷新
            mock_time.return_value = 80.0
            cats4 = client.list_voices(force_refresh=True)
            assert cats4[0].materials[0].name == "丁真"
            assert session.get.call_count == 3  # 强制刷新

    def test_find_voice(self):
        session = MagicMock()
        session.headers = {}
        session.get.return_value = _json_resp(
            {
                "categories": [
                    {
                        "id": 1,
                        "title": "热门",
                        "materials": [{"id": 10, "name": "丁真", "voice": "dingzhen"}],
                    }
                ]
            }
        )

        client = BCutTTSClient(session=session)
        voice = client.find_voice("dingzhen")
        assert voice is not None
        assert voice.name == "丁真"
        assert client.find_voice("notexist") is None

    def test_find_voice_by_name(self):
        """测试只按 name 匹配"""
        session = MagicMock()
        session.headers = {}
        session.get.return_value = _json_resp(
            {
                "categories": [
                    {
                        "id": 1,
                        "title": "热门",
                        "materials": [
                            {"id": 10, "name": "丁真", "voice": "dingzhen"},
                            {"id": 11, "name": "丁真2", "voice": "dingzhen2"},
                        ],
                    }
                ]
            }
        )

        client = BCutTTSClient(session=session)
        voice = client.find_voice_by_name("丁真")
        assert voice is not None
        assert voice.name == "丁真"
        assert voice.voice == "dingzhen"
        assert client.find_voice_by_name("dingzhen") is None  # 不匹配 voice 字段

    def test_find_voice_by_id(self):
        """测试只按 voice ID 匹配"""
        session = MagicMock()
        session.headers = {}
        session.get.return_value = _json_resp(
            {
                "categories": [
                    {
                        "id": 1,
                        "title": "热门",
                        "materials": [
                            {"id": 10, "name": "丁真", "voice": "dingzhen"},
                            {"id": 11, "name": "丁真2", "voice": "dingzhen2"},
                        ],
                    }
                ]
            }
        )

        client = BCutTTSClient(session=session)
        voice = client.find_voice_by_id("dingzhen")
        assert voice is not None
        assert voice.voice == "dingzhen"
        assert voice.name == "丁真"
        assert client.find_voice_by_id("丁真") is None  # 不匹配 name 字段

    def test_create_task(self):
        session = MagicMock()
        session.headers = {}
        session.post.return_value = _json_resp(
            {"task_id": "t1", "poll_time": 1, "result": "", "mark": 0}
        )

        client = BCutTTSClient(session=session)
        tid = client.create_task("你好")
        assert tid == "t1"

    def test_query_result(self):
        data = TTSResultData(audio_url="http://a1")
        session = MagicMock()
        session.headers = {}
        session.get.return_value = _json_resp(
            {
                "task_id": "t1",
                "poll_time": 1,
                "result": data.model_dump_json(),
                "mark": 0,
                "state": 0,
                "remark": "",
            }
        )

        client = BCutTTSClient(session=session)
        result = client.query_result("t1")
        assert result.is_complete()
        assert result.parse().audio_url == "http://a1"

    @patch("bcut_asr_skill.client.time.time")
    def test_synthesize_success(self, mock_time):
        mock_time.side_effect = [0, 0.5, 1.0]

        tts_data = TTSResultData(audio_url="http://a1")
        session = MagicMock()
        session.headers = {}
        session.post.return_value = _json_resp(
            {"task_id": "t1", "poll_time": 1, "result": "", "mark": 0}
        )
        session.get.side_effect = [
            _json_resp(
                {
                    "task_id": "t1",
                    "poll_time": 1,
                    "result": tts_data.model_dump_json(),
                    "mark": 0,
                    "state": 0,
                    "remark": "",
                }
            ),
            MagicMock(status_code=200, content=b"audio_data", raise_for_status=lambda: None),
        ]

        client = BCutTTSClient(session=session)
        with patch("pathlib.Path.write_bytes") as mock_write:
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                path = client.synthesize("你好", "/tmp/out.wav", timeout=5.0)
                assert path == "/tmp/out.wav"
                mock_write.assert_called_once_with(b"audio_data")
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_synthesize_creates_parent_dir(self):
        """测试 TTS synthesize 自动创建父目录"""
        tts_data = TTSResultData(audio_url="http://a1")
        session = MagicMock()
        session.headers = {}
        session.post.return_value = _json_resp(
            {"task_id": "t1", "poll_time": 1, "result": "", "mark": 0}
        )
        session.get.side_effect = [
            _json_resp(
                {
                    "task_id": "t1",
                    "poll_time": 1,
                    "result": tts_data.model_dump_json(),
                    "mark": 0,
                    "state": 0,
                    "remark": "",
                }
            ),
            MagicMock(status_code=200, content=b"audio_data", raise_for_status=lambda: None),
        ]

        client = BCutTTSClient(session=session)
        with patch("pathlib.Path.write_bytes") as mock_write:
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                path = client.synthesize("你好", "/tmp/nested/dir/out.wav")
                assert path == "/tmp/nested/dir/out.wav"
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 异步 ASR 客户端测试
# ---------------------------------------------------------------------------


class TestAsyncBCutASRClient:
    @pytest.mark.asyncio
    async def test_upload_success(self):
        client_mock = MagicMock()
        client_mock.post = AsyncMock()
        client_mock.get = AsyncMock()
        client_mock.put = AsyncMock()
        client_mock.post.side_effect = [
            _json_resp(
                {
                    "resource_id": "r1",
                    "title": "a.mp3",
                    "type": 2,
                    "in_boss_key": "bk",
                    "size": 10,
                    "upload_urls": ["http://up"],
                    "upload_id": "uid",
                    "per_size": 10,
                }
            ),
            _json_resp({"resource_id": "r1", "download_url": "http://dl"}),
        ]
        client_mock.put.return_value = _json_resp({})

        client = AsyncBCutASRClient(client=client_mock)
        url = await client.upload("a.mp3", b"0123456789", "mp3")
        assert url == "http://dl"

    @pytest.mark.asyncio
    async def test_create_task(self):
        client_mock = MagicMock()
        client_mock.post = AsyncMock()
        client_mock.get = AsyncMock()
        client_mock.put = AsyncMock()
        client_mock.post.return_value = _json_resp({"task_id": "t1"})

        client = AsyncBCutASRClient(client=client_mock)
        tid = await client.create_task("http://dl")
        assert tid == "t1"

    @pytest.mark.asyncio
    async def test_query_result(self):
        asr_json = ASRData(
            utterances=[ASRDataSeg(start_time=0, end_time=1000, transcript="hi")]
        ).model_dump_json()
        client_mock = MagicMock()
        client_mock.post = AsyncMock()
        client_mock.get = AsyncMock()
        client_mock.put = AsyncMock()
        client_mock.get.return_value = _json_resp(
            {"task_id": "t1", "result": asr_json, "state": 4}
        )

        client = AsyncBCutASRClient(client=client_mock)
        result = await client.query_result("t1")
        assert result.state == ResultStateEnum.COMPLETE

    @pytest.mark.asyncio
    @patch("bcut_asr_skill.client.read_media_file", return_value=(b"audio", "mp3"))
    @patch("bcut_asr_skill.client.time.time")
    @patch("bcut_asr_skill.client.asyncio.sleep", return_value=None)
    async def test_transcribe_success(self, mock_sleep, mock_time, mock_read):
        mock_time.side_effect = [0, 0.5, 1.0]

        asr_json = ASRData(
            utterances=[ASRDataSeg(start_time=0, end_time=1000, transcript="async")]
        ).model_dump_json()

        client_mock = MagicMock()
        client_mock.post = AsyncMock()
        client_mock.get = AsyncMock()
        client_mock.put = AsyncMock()
        client_mock.post.side_effect = [
            _json_resp(
                {
                    "resource_id": "r1",
                    "title": "x.mp3",
                    "type": 2,
                    "in_boss_key": "bk",
                    "size": 5,
                    "upload_urls": ["http://up"],
                    "upload_id": "uid",
                    "per_size": 5,
                }
            ),
            _json_resp({"resource_id": "r1", "download_url": "http://dl"}),
            _json_resp({"task_id": "t1"}),
        ]
        client_mock.put.return_value = _json_resp({})
        client_mock.get.return_value = _json_resp(
            {"task_id": "t1", "result": asr_json, "state": 4}
        )

        client = AsyncBCutASRClient(client=client_mock)
        out = await client.transcribe("x.mp3", output_format=OutputFormat.TXT, timeout=5.0)
        assert out == "async"


# ---------------------------------------------------------------------------
# 异步 TTS 客户端测试
# ---------------------------------------------------------------------------


class TestAsyncBCutTTSClient:
    @pytest.mark.asyncio
    async def test_list_voices(self):
        client_mock = MagicMock()
        client_mock.post = AsyncMock()
        client_mock.get = AsyncMock()
        client_mock.put = AsyncMock()
        client_mock.get.return_value = _json_resp(
            {
                "categories": [
                    {
                        "id": 1,
                        "title": "热门",
                        "materials": [{"id": 10, "name": "丁真", "voice": "dingzhen"}],
                    }
                ]
            }
        )

        client = AsyncBCutTTSClient(client=client_mock)
        cats = await client.list_voices()
        assert cats[0].materials[0].voice == "dingzhen"

    @pytest.mark.asyncio
    async def test_create_task(self):
        client_mock = MagicMock()
        client_mock.post = AsyncMock()
        client_mock.get = AsyncMock()
        client_mock.put = AsyncMock()
        client_mock.post.return_value = _json_resp({"task_id": "t1"})

        client = AsyncBCutTTSClient(client=client_mock)
        tid = await client.create_task("你好")
        assert tid == "t1"

    @pytest.mark.asyncio
    async def test_query_result(self):
        data = TTSResultData(audio_url="http://a1")
        client_mock = MagicMock()
        client_mock.post = AsyncMock()
        client_mock.get = AsyncMock()
        client_mock.put = AsyncMock()
        client_mock.get.return_value = _json_resp(
            {
                "task_id": "t1",
                "poll_time": 1,
                "result": data.model_dump_json(),
                "mark": 0,
                "state": 0,
                "remark": "",
            }
        )

        client = AsyncBCutTTSClient(client=client_mock)
        result = await client.query_result("t1")
        assert result.is_complete()

    @pytest.mark.asyncio
    @patch("bcut_asr_skill.client.time.time")
    @patch("bcut_asr_skill.client.asyncio.sleep", return_value=None)
    async def test_synthesize_success(self, mock_sleep, mock_time):
        mock_time.side_effect = [0, 0.5, 1.0]

        tts_data = TTSResultData(audio_url="http://a1")
        client_mock = MagicMock()
        client_mock.post = AsyncMock()
        client_mock.get = AsyncMock()
        client_mock.put = AsyncMock()
        client_mock.post.return_value = _json_resp({"task_id": "t1"})

        get_resp = _json_resp(
            {
                "task_id": "t1",
                "poll_time": 1,
                "result": tts_data.model_dump_json(),
                "mark": 0,
                "state": 0,
                "remark": "",
            }
        )
        client_mock.get.return_value = get_resp

        async def _fake_aiter():
            for chunk in [b"chunk1", b"chunk2"]:
                yield chunk
        
        stream_resp = AsyncMock()
        stream_resp.status_code = 200
        stream_resp.raise_for_status = AsyncMock(return_value=None)
        stream_resp.aiter_bytes = _fake_aiter
        
        stream_ctx = AsyncMock()
        stream_ctx.__aenter__ = AsyncMock(return_value=stream_resp)
        stream_ctx.__aexit__ = AsyncMock(return_value=None)
        client_mock.stream = MagicMock(return_value=stream_ctx)

        client = AsyncBCutTTSClient(client=client_mock)
        with patch("builtins.open", MagicMock()) as mock_open:
            path = await client.synthesize("你好", "/tmp/out.wav", timeout=5.0)
            assert path == "/tmp/out.wav"
