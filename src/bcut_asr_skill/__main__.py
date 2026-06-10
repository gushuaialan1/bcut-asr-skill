"""模块直接运行入口

python -m bcut_asr_skill [--asr|--tts] ...
"""

from __future__ import annotations

import argparse
import sys

from .cli import main, main_tts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bcut_asr_skill",
        description="BCut ASR/TTS Skill CLI",
    )
    parser.add_argument(
        "--tts",
        action="store_true",
        help="使用 TTS 模式 (默认 ASR)",
    )
    # 剩余参数透传给子命令
    parser.add_argument("args", nargs=argparse.REMAINDER, help="子命令参数")
    return parser


def run() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.tts:
        return main_tts(args.args)
    return main(args.args)


if __name__ == "__main__":
    sys.exit(run())
