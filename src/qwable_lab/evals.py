from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .client import OpenAICompatibleClient


DEFAULT_SYSTEM = (
    "You are being evaluated. Follow the user's instructions exactly, "
    "be concise when asked, and state uncertainty when needed."
)


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    prompt: str
    system: str = DEFAULT_SYSTEM
    temperature: float | None = None
    max_tokens: int | None = None
    checks: dict[str, list[str]] = field(default_factory=dict)
    notes: str = ""


def load_cases(path: Path, limit: int | None = None) -> list[Case]:
    cases: list[Case] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            cases.append(_case_from_payload(payload, path, line_no))
            if limit is not None and len(cases) >= limit:
                break
    return cases


def run_cases(
    *,
    client: OpenAICompatibleClient,
    model: str,
    cases: list[Case],
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    results = []
    for case in cases:
        result = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": case.system},
                {"role": "user", "content": case.prompt},
            ],
            temperature=case.temperature if case.temperature is not None else temperature,
            max_tokens=case.max_tokens if case.max_tokens is not None else max_tokens,
        )
        score = score_text(result.text, case.checks)
        results.append(
            {
                "id": case.id,
                "category": case.category,
                "prompt": case.prompt,
                "system": case.system,
                "notes": case.notes,
                "checks": case.checks,
                "response": result.text,
                "latency_s": round(result.latency_s, 3),
                "usage": result.usage,
                "score": score,
            }
        )
    return {"model": model, "results": results, "summary": summarize(results)}


def score_text(text: str, checks: dict[str, list[str]]) -> dict[str, Any]:
    lowered = text.lower()
    must_include = checks.get("must_include", [])
    must_avoid = checks.get("must_avoid", [])
    included = [item for item in must_include if item.lower() in lowered]
    missing = [item for item in must_include if item.lower() not in lowered]
    avoided = [item for item in must_avoid if item.lower() not in lowered]
    violations = [item for item in must_avoid if item.lower() in lowered]

    total = len(must_include) + len(must_avoid)
    passed = len(included) + len(avoided)
    ratio = 1.0 if total == 0 else passed / total
    return {
        "ratio": round(ratio, 3),
        "included": included,
        "missing": missing,
        "avoided": avoided,
        "violations": violations,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"cases": 0, "avg_score": 0, "avg_latency_s": 0}
    avg_score = sum(item["score"]["ratio"] for item in results) / len(results)
    avg_latency = sum(item["latency_s"] for item in results) / len(results)
    by_category: dict[str, list[float]] = {}
    for item in results:
        by_category.setdefault(item["category"], []).append(item["score"]["ratio"])
    return {
        "cases": len(results),
        "avg_score": round(avg_score, 3),
        "avg_latency_s": round(avg_latency, 3),
        "by_category": {
            key: round(sum(values) / len(values), 3)
            for key, values in sorted(by_category.items())
        },
    }


def _case_from_payload(payload: dict[str, Any], path: Path, line_no: int) -> Case:
    for field_name in ("id", "category", "prompt"):
        if not isinstance(payload.get(field_name), str) or not payload[field_name].strip():
            raise ValueError(f"{path}:{line_no}: missing string field {field_name!r}")

    checks = payload.get("checks") or {}
    if not isinstance(checks, dict):
        raise ValueError(f"{path}:{line_no}: checks must be an object")
    clean_checks = {}
    for key in ("must_include", "must_avoid"):
        values = checks.get(key, [])
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ValueError(f"{path}:{line_no}: checks.{key} must be a string list")
        clean_checks[key] = values

    return Case(
        id=payload["id"],
        category=payload["category"],
        prompt=payload["prompt"],
        system=payload.get("system") or DEFAULT_SYSTEM,
        temperature=payload.get("temperature"),
        max_tokens=payload.get("max_tokens"),
        checks=clean_checks,
        notes=payload.get("notes") or "",
    )
