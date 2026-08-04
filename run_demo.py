#!/usr/bin/env python3
"""Run the CogniGuide local reference demo or start its browser UI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cogniguide.engine import InputValidationError, run_pipeline, write_artifacts
from cogniguide.server import serve


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CogniGuide deterministic multi-agent demo")
    parser.add_argument("--input", type=Path, help="学习信号 JSON 输入文件")
    parser.add_argument("--output", type=Path, default=Path("runs/latest"), help="产物目录（默认：runs/latest）")
    parser.add_argument("--serve", action="store_true", help="启动本地浏览器演示界面")
    parser.add_argument("--host", default="127.0.0.1", help="Web 服务监听地址（默认：127.0.0.1）")
    parser.add_argument("--port", type=int, default=8080, help="Web 服务端口（默认：8080）")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.serve:
        serve(args.host, args.port)
        return 0
    if args.input is None:
        print("错误：请提供 --input，或使用 --serve 启动浏览器界面。", file=sys.stderr)
        return 2
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = run_pipeline(payload)
    except (OSError, json.JSONDecodeError, InputValidationError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    artifacts = write_artifacts(result, args.output)
    print(f"状态: {result['status']}")
    print(f"运行 ID: {result['run_id']}")
    print("产物:")
    for name, path in artifacts.items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
