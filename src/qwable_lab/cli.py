from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .client import OpenAICompatibleClient
from .evals import load_cases, run_cases
from .hf import REPO_ID, choose_quant_file, fetch_model_info, find_mmproj
from .report import load_json_report, write_html_report, write_json_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qwable-lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("models", help="Show current Hugging Face metadata.")

    download = subparsers.add_parser("download-command", help="Print a Hugging Face download command.")
    download.add_argument("--quant", default="Q4_K_M_Q8", help="Quantization substring to select.")
    download.add_argument("--local-dir", default="models/qwable", help="Target local model directory.")
    download.add_argument(
        "--gpu-layers",
        default="0",
        help="Value for llama.cpp -ngl. Use 0 for the bundled CPU build, 99/auto for a GPU build.",
    )

    smoke = subparsers.add_parser("smoke", help="Check an OpenAI-compatible endpoint.")
    smoke.add_argument("--endpoint", required=True)
    smoke.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"))

    run = subparsers.add_parser("run", help="Run a scenario file.")
    run.add_argument("--endpoint", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--scenario", default="scenarios/default.jsonl")
    run.add_argument("--out", default="runs/latest.json")
    run.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"))
    run.add_argument("--temperature", type=float, default=0.2)
    run.add_argument("--max-tokens", type=int, default=700)
    run.add_argument("--timeout", type=int, default=180)
    run.add_argument("--limit", type=int)

    report = subparsers.add_parser("report", help="Render a JSON run as HTML.")
    report.add_argument("--run", default="runs/latest.json")
    report.add_argument("--out", default="reports/latest.html")

    args = parser.parse_args(argv)
    if args.command == "models":
        return _models()
    if args.command == "download-command":
        return _download_command(args)
    if args.command == "smoke":
        return _smoke(args)
    if args.command == "run":
        return _run(args)
    if args.command == "report":
        return _report(args)
    parser.error(f"unknown command {args.command}")
    return 2


def _models() -> int:
    info = fetch_model_info()
    print(f"repo: {info.repo_id}")
    print(f"sha: {info.sha}")
    print(f"last_modified: {info.last_modified}")
    print(f"downloads: {info.downloads}")
    print(f"likes: {info.likes}")
    print(f"license: {info.license}")
    print(f"architecture: {info.architecture}")
    print(f"context_length: {info.context_length}")
    print("files:")
    for file in info.files:
        print(f"  - {file.name} ({file.size_gb})")
    return 0


def _download_command(args: argparse.Namespace) -> int:
    info = fetch_model_info()
    model_file = choose_quant_file(info, args.quant)
    mmproj = find_mmproj(info)
    server_bin = "./bin/llama-server" if Path("bin/llama-server").exists() else "llama-server"
    include_args = [model_file.name]
    if mmproj is not None:
        include_args.append(mmproj.name)
    for name in include_args:
        print(f"hf download {REPO_ID} {name} --local-dir {args.local_dir}")
    print()
    print("llama.cpp server shape:")
    print(
        f"{server_bin} "
        f"-m {args.local_dir}/{model_file.name} "
        + (f"--mmproj {args.local_dir}/{mmproj.name} " if mmproj else "")
        + f"--jinja -c 32768 -ngl {args.gpu_layers} --host 127.0.0.1 --port 8080"
    )
    print()
    print("Note: the bundled CPU build has no HTTPS support; download first, then run with -m.")
    return 0


def _smoke(args: argparse.Namespace) -> int:
    client = OpenAICompatibleClient(args.endpoint, api_key=args.api_key)
    payload = client.list_models()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run(args: argparse.Namespace) -> int:
    scenario = Path(args.scenario)
    cases = load_cases(scenario, limit=args.limit)
    client = OpenAICompatibleClient(args.endpoint, api_key=args.api_key, timeout=args.timeout)
    payload = run_cases(
        client=client,
        model=args.model,
        cases=cases,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    payload["scenario"] = str(scenario)
    payload["endpoint"] = args.endpoint
    out = Path(args.out)
    write_json_report(payload, out)
    print(f"Wrote {out} with {len(cases)} cases.")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    return 0


def _report(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = load_json_report(Path(args.run))
    out = Path(args.out)
    write_html_report(payload, out)
    print(f"Wrote {out}")
    return 0
