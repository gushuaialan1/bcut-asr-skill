"""BCut ASR / TTS HTTP 客户端

同时提供同步 (requests) 与异步 (httpx) 实现，
支持上下文管理器自动释放会话资源。
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import httpx
import requests

from .exceptions import APIError, TaskTimeoutError
from .formats import OutputFormat, convert
from .models import (
    ASRData,
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
from .utils import read_media_file

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

ASR_API_BASE = "https://member.bilibili.com/x/bcut/rubick-interface"
API_REQ_UPLOAD = f"{ASR_API_BASE}/resource/create"
API_COMMIT_UPLOAD = f"{ASR_API_BASE}/resource/create/complete"
API_CREATE_TASK = f"{ASR_API_BASE}/task"
API_QUERY_RESULT = f"{ASR_API_BASE}/task/result"
ASR_MODEL_ID = "7"

TTS_API_BASE = "https://member.bilibili.com"
API_TTS_VOICES = f"{TTS_API_BASE}/x/creative-tool/bcut/pc/tts/list"
API_TTS_TASK = f"{TTS_API_BASE}/x/creative-tool/rubick-interface/task"
API_TTS_RESULT = f"{TTS_API_BASE}/x/creative-tool/rubick-interface/task/result"
TTS_MODEL_ID = "tts_common_bcut_pc"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://member.bilibili.com",
}


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _check_resp(data: dict) -> dict:
    """检查 B站 API 响应，业务错误时抛 APIError"""
    code = data.get("code", 0)
    if code != 0:
        raise APIError(code, data.get("message", "未知错误"))
    return data.get("data", {})


# ---------------------------------------------------------------------------
# 同步 ASR 客户端
# ---------------------------------------------------------------------------

class BCutASRClient:
    """必剪语音识别同步客户端"""

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._task_id: Optional[str] = None

    def _post(self, url: str, **kwargs) -> dict:
        """封装 POST 请求 + 响应校验"""
        resp = self.session.post(url, **kwargs)
        resp.raise_for_status()
        return _check_resp(resp.json())

    def _get(self, url: str, **kwargs) -> dict:
        """封装 GET 请求 + 响应校验"""
        resp = self.session.get(url, **kwargs)
        resp.raise_for_status()
        return _check_resp(resp.json())

    def upload(self, sound_name: str, sound_bin: bytes, sound_fmt: str) -> str:
        """上传音频文件，返回下载 URL"""
        # 1. 申请上传
        create_data = self._post(
            API_REQ_UPLOAD,
            data={
                "type": 2,
                "name": sound_name,
                "size": len(sound_bin),
                "resource_file_type": sound_fmt,
                "model_id": ASR_MODEL_ID,
            },
        )
        create_rsp = ResourceCreateRspSchema.model_validate(create_data)
        logger.info(
            f"申请上传成功: {len(sound_bin)} bytes, "
            f"{len(create_rsp.upload_urls)} 分片"
        )

        # 2. 分片上传
        etags: list[str] = []
        for clip, url in enumerate(create_rsp.upload_urls):
            start = clip * create_rsp.per_size
            end = start + create_rsp.per_size
            put_resp = self.session.put(url, data=sound_bin[start:end])
            put_resp.raise_for_status()
            etags.append(put_resp.headers.get("Etag", ""))
            logger.info(f"分片 {clip} 上传成功")

        # 3. 提交上传
        commit_data = self._post(
            API_COMMIT_UPLOAD,
            data={
                "in_boss_key": create_rsp.in_boss_key,
                "resource_id": create_rsp.resource_id,
                "etags": ",".join(etags),
                "upload_id": create_rsp.upload_id,
                "model_id": ASR_MODEL_ID,
            },
        )
        commit_rsp = ResourceCompleteRspSchema.model_validate(commit_data)
        logger.info("上传提交成功")
        return commit_rsp.download_url

    def create_task(self, download_url: str) -> str:
        """创建识别任务，返回 task_id"""
        data = self._post(
            API_CREATE_TASK,
            json={"resource": download_url, "model_id": ASR_MODEL_ID},
        )
        rsp = TaskCreateRspSchema.model_validate(data)
        self._task_id = rsp.task_id
        logger.info(f"任务已创建: {self._task_id}")
        return rsp.task_id

    def query_result(self, task_id: Optional[str] = None) -> ResultRspSchema:
        """查询任务结果"""
        data = self._get(
            API_QUERY_RESULT,
            params={"model_id": ASR_MODEL_ID, "task_id": task_id or self._task_id},
        )
        return ResultRspSchema.model_validate(data)

    def transcribe(
        self,
        file_path: str,
        *,
        output_format: OutputFormat = OutputFormat.SRT,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> str:
        """一站式语音识别：上传 → 创建任务 → 轮询 → 返回指定格式文本

        Args:
            file_path: 媒体文件路径 (支持视频自动 ffmpeg 提取)
            output_format: 输出格式
            poll_interval: 轮询间隔 (秒)
            timeout: 总超时 (秒)

        Returns:
            格式化后的识别结果字符串
        """
        sound_bin, sound_fmt = read_media_file(file_path)
        sound_name = Path(file_path).name

        download_url = self.upload(sound_name, sound_bin, sound_fmt)
        self.create_task(download_url)

        start = time.time()
        while True:
            if time.time() - start > timeout:
                raise TaskTimeoutError(f"ASR 任务超时 ({timeout}s)")

            result = self.query_result()
            match result.state:
                case ResultStateEnum.STOP:
                    logger.info("等待识别开始...")
                case ResultStateEnum.RUNNING:
                    logger.info(f"识别中: {result.remark}")
                case ResultStateEnum.ERROR:
                    raise APIError(-1, f"识别失败: {result.remark}")
                case ResultStateEnum.COMPLETE:
                    asr_data = result.parse()
                    if not asr_data.has_data():
                        raise APIError(-1, "未识别到语音")
                    logger.info("识别成功")
                    return convert(asr_data, output_format)

            time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# 同步 TTS 客户端
# ---------------------------------------------------------------------------

class BCutTTSClient:
    """必剪语音合成同步客户端"""

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._voices: Optional[list[VoiceCategory]] = None

    def list_voices(self, force_refresh: bool = False) -> list[VoiceCategory]:
        """获取可用音色列表"""
        if self._voices is not None and not force_refresh:
            return self._voices

        resp = self.session.get(API_TTS_VOICES)
        resp.raise_for_status()
        data = _check_resp(resp.json())

        categories: list[VoiceCategory] = []
        for cat_data in data.get("categories", []):
            materials: list[VoiceMaterial] = []
            for mat_data in cat_data.get("materials", []):
                ssml_effect = ""
                extra = mat_data.get("extra", "")
                if extra:
                    try:
                        ssml_effect = json.loads(extra).get("ssml_effect", "")
                    except Exception:
                        pass
                materials.append(
                    VoiceMaterial(
                        **{k: v for k, v in mat_data.items() if k != "extra"},
                        ssml_effect=ssml_effect,
                    )
                )
            categories.append(
                VoiceCategory(
                    id=cat_data["id"],
                    title=cat_data["title"],
                    cover=cat_data.get("cover", ""),
                    materials=materials,
                    rank=cat_data.get("rank", 0),
                )
            )
        self._voices = categories
        logger.info(f"获取音色列表成功，共 {len(categories)} 个分类")
        return categories

    def find_voice(self, name: str) -> Optional[VoiceMaterial]:
        """根据 voice 值或名称查找音色"""
        for cat in self.list_voices():
            for mat in cat.materials:
                if mat.voice == name or mat.name == name:
                    return mat
        return None

    def create_task(
        self,
        text: str,
        voice: str = "dingzhen",
        pitch: int = 0,
        speed: int = 0,
        volume: int = 100,
    ) -> str:
        """创建 TTS 任务，返回 task_id"""
        params = TTSParams(
            pitch_rate=pitch, speech_rate=speed, voice=voice, volume=volume
        )
        payload = {
            "model_id": TTS_MODEL_ID,
            "params": json.dumps({
                "expect_mark": 0,
                "raw_data": text,
                "raw_params": params.model_dump(),
            }),
        }
        resp = self.session.post(API_TTS_TASK, json=payload)
        resp.raise_for_status()
        data = _check_resp(resp.json())
        rsp = TaskCreateRspSchema.model_validate(data)
        logger.info(f"TTS 任务已创建: {rsp.task_id}")
        return rsp.task_id

    def query_result(self, task_id: str) -> TTSResultRspSchema:
        """查询 TTS 任务结果"""
        resp = self.session.get(
            API_TTS_RESULT,
            params={"model_id": TTS_MODEL_ID, "task_id": task_id},
        )
        resp.raise_for_status()
        data = _check_resp(resp.json())
        return TTSResultRspSchema.model_validate(data)

    def synthesize(
        self,
        text: str,
        output_path: str,
        *,
        voice: str = "dingzhen",
        pitch: int = 0,
        speed: int = 0,
        volume: int = 100,
        poll_interval: float = 1.0,
        timeout: float = 60.0,
    ) -> str:
        """一站式语音合成：创建任务 → 轮询 → 下载保存

        Returns:
            保存的文件路径
        """
        task_id = self.create_task(text, voice, pitch, speed, volume)

        start = time.time()
        while True:
            if time.time() - start > timeout:
                raise TaskTimeoutError(f"TTS 任务超时 ({timeout}s)")

            result = self.query_result(task_id)
            if result.is_complete():
                tts_data = result.parse()
                logger.info("TTS 任务完成，开始下载")
                break
            if result.state == 3:
                raise APIError(-1, f"TTS 任务失败: {result.remark}")

            logger.info(f"TTS 处理中... (state={result.state})")
            time.sleep(poll_interval)

        # 下载音频
        audio_resp = self.session.get(tts_data.audio_url)
        audio_resp.raise_for_status()
        Path(output_path).write_bytes(audio_resp.content)
        logger.info(f"音频已保存: {output_path}")
        return output_path


# ---------------------------------------------------------------------------
# 异步 ASR 客户端
# ---------------------------------------------------------------------------

class AsyncBCutASRClient:
    """必剪语音识别异步客户端 (httpx)"""

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self.client = client or httpx.AsyncClient(headers=DEFAULT_HEADERS)
        self._own_client = client is None
        self._task_id: Optional[str] = None

    async def close(self) -> None:
        if self._own_client:
            await self.client.aclose()

    async def __aenter__(self) -> AsyncBCutASRClient:
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    async def _post(self, url: str, **kwargs) -> dict:
        resp = await self.client.post(url, **kwargs)
        resp.raise_for_status()
        return _check_resp(resp.json())

    async def _get(self, url: str, **kwargs) -> dict:
        resp = await self.client.get(url, **kwargs)
        resp.raise_for_status()
        return _check_resp(resp.json())

    async def upload(self, sound_name: str, sound_bin: bytes, sound_fmt: str) -> str:
        """异步上传音频"""
        create_data = await self._post(
            API_REQ_UPLOAD,
            data={
                "type": 2,
                "name": sound_name,
                "size": len(sound_bin),
                "resource_file_type": sound_fmt,
                "model_id": ASR_MODEL_ID,
            },
        )
        create_rsp = ResourceCreateRspSchema.model_validate(create_data)

        etags: list[str] = []
        for clip, url in enumerate(create_rsp.upload_urls):
            start = clip * create_rsp.per_size
            end = start + create_rsp.per_size
            put_resp = await self.client.put(url, content=sound_bin[start:end])
            put_resp.raise_for_status()
            etags.append(put_resp.headers.get("Etag", ""))

        commit_data = await self._post(
            API_COMMIT_UPLOAD,
            data={
                "in_boss_key": create_rsp.in_boss_key,
                "resource_id": create_rsp.resource_id,
                "etags": ",".join(etags),
                "upload_id": create_rsp.upload_id,
                "model_id": ASR_MODEL_ID,
            },
        )
        commit_rsp = ResourceCompleteRspSchema.model_validate(commit_data)
        return commit_rsp.download_url

    async def create_task(self, download_url: str) -> str:
        data = await self._post(
            API_CREATE_TASK,
            json={"resource": download_url, "model_id": ASR_MODEL_ID},
        )
        rsp = TaskCreateRspSchema.model_validate(data)
        self._task_id = rsp.task_id
        return rsp.task_id

    async def query_result(self, task_id: Optional[str] = None) -> ResultRspSchema:
        data = await self._get(
            API_QUERY_RESULT,
            params={"model_id": ASR_MODEL_ID, "task_id": task_id or self._task_id},
        )
        return ResultRspSchema.model_validate(data)

    async def transcribe(
        self,
        file_path: str,
        *,
        output_format: OutputFormat = OutputFormat.SRT,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> str:
        """异步一站式语音识别"""
        sound_bin, sound_fmt = read_media_file(file_path)
        sound_name = Path(file_path).name

        download_url = await self.upload(sound_name, sound_bin, sound_fmt)
        await self.create_task(download_url)

        start = time.time()
        while True:
            if time.time() - start > timeout:
                raise TaskTimeoutError(f"ASR 任务超时 ({timeout}s)")

            result = await self.query_result()
            match result.state:
                case ResultStateEnum.STOP:
                    logger.info("等待识别开始...")
                case ResultStateEnum.RUNNING:
                    logger.info(f"识别中: {result.remark}")
                case ResultStateEnum.ERROR:
                    raise APIError(-1, f"识别失败: {result.remark}")
                case ResultStateEnum.COMPLETE:
                    asr_data = result.parse()
                    if not asr_data.has_data():
                        raise APIError(-1, "未识别到语音")
                    return convert(asr_data, output_format)

            await asyncio.sleep(poll_interval)


# ---------------------------------------------------------------------------
# 异步 TTS 客户端
# ---------------------------------------------------------------------------

class AsyncBCutTTSClient:
    """必剪语音合成异步客户端 (httpx)"""

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self.client = client or httpx.AsyncClient(headers=DEFAULT_HEADERS)
        self._own_client = client is None
        self._voices: Optional[list[VoiceCategory]] = None

    async def close(self) -> None:
        if self._own_client:
            await self.client.aclose()

    async def __aenter__(self) -> AsyncBCutTTSClient:
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    async def list_voices(self, force_refresh: bool = False) -> list[VoiceCategory]:
        """异步获取音色列表"""
        if self._voices is not None and not force_refresh:
            return self._voices

        resp = await self.client.get(API_TTS_VOICES)
        resp.raise_for_status()
        data = _check_resp(resp.json())

        categories: list[VoiceCategory] = []
        for cat_data in data.get("categories", []):
            materials: list[VoiceMaterial] = []
            for mat_data in cat_data.get("materials", []):
                ssml_effect = ""
                extra = mat_data.get("extra", "")
                if extra:
                    try:
                        ssml_effect = json.loads(extra).get("ssml_effect", "")
                    except Exception:
                        pass
                materials.append(
                    VoiceMaterial(
                        **{k: v for k, v in mat_data.items() if k != "extra"},
                        ssml_effect=ssml_effect,
                    )
                )
            categories.append(
                VoiceCategory(
                    id=cat_data["id"],
                    title=cat_data["title"],
                    cover=cat_data.get("cover", ""),
                    materials=materials,
                    rank=cat_data.get("rank", 0),
                )
            )
        self._voices = categories
        return categories

    async def find_voice(self, name: str) -> Optional[VoiceMaterial]:
        for cat in await self.list_voices():
            for mat in cat.materials:
                if mat.voice == name or mat.name == name:
                    return mat
        return None

    async def create_task(
        self,
        text: str,
        voice: str = "dingzhen",
        pitch: int = 0,
        speed: int = 0,
        volume: int = 100,
    ) -> str:
        params = TTSParams(
            pitch_rate=pitch, speech_rate=speed, voice=voice, volume=volume
        )
        payload = {
            "model_id": TTS_MODEL_ID,
            "params": json.dumps({
                "expect_mark": 0,
                "raw_data": text,
                "raw_params": params.model_dump(),
            }),
        }
        resp = await self.client.post(API_TTS_TASK, json=payload)
        resp.raise_for_status()
        data = _check_resp(resp.json())
        rsp = TaskCreateRspSchema.model_validate(data)
        return rsp.task_id

    async def query_result(self, task_id: str) -> TTSResultRspSchema:
        resp = await self.client.get(
            API_TTS_RESULT,
            params={"model_id": TTS_MODEL_ID, "task_id": task_id},
        )
        resp.raise_for_status()
        data = _check_resp(resp.json())
        return TTSResultRspSchema.model_validate(data)

    async def synthesize(
        self,
        text: str,
        output_path: str,
        *,
        voice: str = "dingzhen",
        pitch: int = 0,
        speed: int = 0,
        volume: int = 100,
        poll_interval: float = 1.0,
        timeout: float = 60.0,
    ) -> str:
        """异步一站式语音合成"""
        task_id = await self.create_task(text, voice, pitch, speed, volume)

        start = time.time()
        while True:
            if time.time() - start > timeout:
                raise TaskTimeoutError(f"TTS 任务超时 ({timeout}s)")

            result = await self.query_result(task_id)
            if result.is_complete():
                tts_data = result.parse()
                break
            if result.state == 3:
                raise APIError(-1, f"TTS 任务失败: {result.remark}")

            await asyncio.sleep(poll_interval)

        # 异步流式下载
        async with self.client.stream("GET", tts_data.audio_url) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                async for chunk in resp.aiter_bytes():
                    f.write(chunk)
        return output_path


# 延迟导入 asyncio，避免顶层依赖
import asyncio  # noqa: E402
