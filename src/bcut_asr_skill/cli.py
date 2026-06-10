"""命令行接口

提供 bcut-asr 与 bcut-tts 两个子命令入口。
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .client import BCutASRClient, BCutTTSClient
from .exceptions import APIError, BCutError
from .formats import OutputFormat
from .utils import guess_output_format
from . import __version__

logger = logging.getLogger(__name__)

INFILE_FMT = ["flac", "aac", "m4a", "mp3", "wav"]
OUTFILE_FMT = ["srt", "lrc", "txt", "json"]


def _setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s - [%(levelname)s] %(message)s",
        level=logging.INFO,
    )


def _build_asr_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bcut-asr",
        description="必剪语音识别 - 将音频/视频转换为字幕",
        epilog=f"支持输入格式: {', '.join(INFILE_FMT)} (视频会自动 ffmpeg 提取伴音)",
    )
    parser.add_argument("--version", action="version", version=f"bcut-asr {__version__}")
    parser.add_argument("input", help="输入媒体文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出字幕文件路径")
    parser.add_argument(
        "-f", "--format", choices=OUTFILE_FMT, default=None,
        help="输出格式 (默认根据输出文件后缀推断，否则 srt)",
    )
    parser.add_argument(
        "-i", "--interval", type=float, default=1.0,
        help="任务状态轮询间隔 (秒，默认 1.0)",
    )
    parser.add_argument(
        "-t", "--timeout", type=float, default=300.0,
        help="总超时时间 (秒，默认 300)",
    )
    return parser


def _build_tts_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bcut-tts",
        description="必剪语音合成 - 文本转语音",
        epilog="使用 -l 列出所有可用音色",
    )
    parser.add_argument("--version", action="version", version=f"bcut-tts {__version__}")
    parser.add_argument("text", nargs="?", help="要合成的文本内容")
    parser.add_argument("-o", "--output", default="output.wav", help="输出音频路径")
    parser.add_argument("-v", "--voice", default="dingzhen", help="音色名称")
    parser.add_argument("--pitch", type=int, default=0, help="音调调整 (-300~300)")
    parser.add_argument("--speed", type=int, default=0, help="语速调整 (-300~300)")
    parser.add_argument("--volume", type=int, default=100, help="音量 (0~100)")
    parser.add_argument(
        "-i", "--interval", type=float, default=1.0,
        help="轮询间隔 (秒，默认 1.0)",
    )
    parser.add_argument(
        "-t", "--timeout", type=float, default=60.0,
        help="超时时间 (秒，默认 60)",
    )
    parser.add_argument("-l", "--list-voices", action="store_true", help="列出所有音色")
    return parser


def main(argv: list[str] | None = None) -> int:
    """bcut-asr 入口"""
    _setup_logging()
    parser = _build_asr_parser()
    args = parser.parse_args(argv)

    output_fmt = guess_output_format(args.output, args.format or "srt")
    try:
        fmt_enum = OutputFormat(output_fmt)
    except ValueError:
        logger.error(f"不支持的输出格式: {output_fmt}")
        return 1

    client = BCutASRClient()
    try:
        result = client.transcribe(
            args.input,
            output_format=fmt_enum,
            poll_interval=args.interval,
            timeout=args.timeout,
        )
    except BCutError as exc:
        logger.error(str(exc))
        return 1

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        logger.info(f"已保存: {args.output}")
    else:
        # 默认输出到同目录
        base = Path(args.input).stem
        out_path = Path(f"{base}.{output_fmt}")
        out_path.write_text(result, encoding="utf-8")
        logger.info(f"已保存: {out_path}")
    return 0


def main_tts(argv: list[str] | None = None) -> int:
    """bcut-tts 入口"""
    _setup_logging()
    parser = _build_tts_parser()
    args = parser.parse_args(argv)

    client = BCutTTSClient()

    if args.list_voices:
        try:
            categories = client.list_voices()
            for cat in categories:
                print(f"\n【{cat.title}】")
                for mat in cat.materials:
                    tag = "B站" if mat.voice_engine == "bili-fewshot" else "MiniMax"
                    extras = []
                    if mat.tts_tags:
                        extras.append(mat.tts_tags)
                    if mat.ssml_effect:
                        extras.append(f"效果:{mat.ssml_effect}")
                    extra_str = f" [{', '.join(extras)}]" if extras else ""
                    print(f"  {mat.name}: {mat.voice} ({tag}){extra_str}")
            return 0
        except APIError as exc:
            logger.error(str(exc))
            return 1

    if not args.text:
        parser.error("请提供要合成的文本内容")
        return 1

    try:
        client.synthesize(
            text=args.text,
            output_path=args.output,
            voice=args.voice,
            pitch=args.pitch,
            speed=args.speed,
            volume=args.volume,
            poll_interval=args.interval,
            timeout=args.timeout,
        )
        logger.info(f"语音合成完成: {args.output}")
        return 0
    except BCutError as exc:
        logger.error(str(exc))
        return 1
