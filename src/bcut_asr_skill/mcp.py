"""
MCP (Model Context Protocol) server for bcut-asr-skill.

Provides ASR and TTS tools for AI agents via stdio JSON-RPC.

Usage:
    python -m bcut_asr_skill.mcp
"""

import json
import sys
from typing import Any

from . import BCutASRClient, BCutTTSClient, OutputFormat


def _send(msg: dict[str, Any]) -> None:
    data = json.dumps(msg)
    sys.stdout.write(f"Content-Length: {len(data)}\r\n\r\n{data}")
    sys.stdout.flush()


def _recv() -> dict[str, Any]:
    headers = {}
    while True:
        line = sys.stdin.readline().strip()
        if not line:
            break
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    length = int(headers.get("Content-Length", 0))
    data = sys.stdin.read(length)
    return json.loads(data)


TOOLS = [
    {
        "name": "bcut_asr_transcribe",
        "description": "Transcribe audio/video to subtitles using Bilibili BCut ASR",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Audio/video file path"},
                "output_format": {"type": "string", "enum": ["srt", "lrc", "txt", "json"], "default": "srt"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "bcut_tts_synthesize",
        "description": "Synthesize speech from text using Bilibili BCut TTS",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "output_path": {"type": "string"},
                "voice": {"type": "string", "default": "dingzhen"},
                "pitch": {"type": "integer", "default": 0},
                "speed": {"type": "integer", "default": 0},
                "volume": {"type": "integer", "default": 100},
            },
            "required": ["text", "output_path"],
        },
    },
    {
        "name": "bcut_tts_list_voices",
        "description": "List all available TTS voices",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _handle_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "bcut_asr_transcribe":
        client = BCutASRClient()
        fmt = OutputFormat[args.get("output_format", "srt").upper()]
        result = client.transcribe(args["file_path"], output_format=fmt)
        return {"content": [{"type": "text", "text": result}]}

    elif name == "bcut_tts_synthesize":
        client = BCutTTSClient()
        path = client.synthesize(
            args["text"],
            args["output_path"],
            voice=args.get("voice", "dingzhen"),
            pitch=args.get("pitch", 0),
            speed=args.get("speed", 0),
            volume=args.get("volume", 100),
        )
        return {"content": [{"type": "text", "text": f"Saved to {path}"}]}

    elif name == "bcut_tts_list_voices":
        client = BCutTTSClient()
        voices = client.list_voices()
        lines = []
        for cat in voices:
            lines.append(f"【{cat.title}】")
            for v in cat.materials:
                lines.append(f"  {v.name} ({v.voice}) - {v.voice_engine}")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    raise ValueError(f"Unknown tool: {name}")


def main() -> None:
    while True:
        try:
            msg = _recv()
        except (EOFError, json.JSONDecodeError):
            break

        method = msg.get("method")
        msg_id = msg.get("id")

        if method == "initialize":
            _send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "bcut-asr-skill", "version": "1.0.0"},
                },
            })
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            params = msg.get("params", {})
            try:
                result = _handle_tool(params["name"], params.get("arguments", {}))
                _send({"jsonrpc": "2.0", "id": msg_id, "result": result})
            except Exception as e:
                _send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": str(e)},
                })
        elif method == "notifications/initialized":
            pass


if __name__ == "__main__":
    main()
