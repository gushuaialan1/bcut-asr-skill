"""自定义异常模块

定义了 BCut ASR/TTS 服务调用过程中可能抛出的所有异常类型，
便于调用方做精确的错误处理。
"""


class BCutError(Exception):
    """BCut Skill 基础异常"""

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(message)


class APIError(BCutError):
    """B站 API 返回业务错误

    Attributes:
        code: API 返回的错误码
        msg: 错误描述信息
    """

    def __init__(self, code: int, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(f"{code}:{msg}")


class FormatError(BCutError):
    """输出格式转换错误"""


class FFmpegError(BCutError):
    """FFmpeg 调用失败"""


class TaskTimeoutError(BCutError):
    """任务轮询超时"""
