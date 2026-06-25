from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_json_report(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_html_report(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = payload.get("summary", {})
    rows = "\n".join(_case_block(item) for item in payload.get("results", []))
    categories = "\n".join(
        f"<li><strong>{html.escape(key)}</strong>: {value}</li>"
        for key, value in (summary.get("by_category") or {}).items()
    )
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Qwable Lab Report</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #18202a;
      --muted: #657080;
      --line: #d8dee8;
      --paper: #f7f8fb;
      --panel: #ffffff;
      --good: #0f766e;
      --warn: #b45309;
      --bad: #b91c1c;
      --accent: #315fbd;
    }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 28px 20px 48px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 20px;
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 24px 0 12px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .meta, .notes {{
      color: var(--muted);
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .metric, article {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric strong {{
      display: block;
      font-size: 24px;
      color: var(--accent);
    }}
    article {{
      margin: 14px 0;
    }}
    .case-head {{
      display: flex;
      gap: 12px;
      justify-content: space-between;
      align-items: baseline;
      border-bottom: 1px solid var(--line);
      padding-bottom: 8px;
      margin-bottom: 10px;
    }}
    .score-good {{ color: var(--good); }}
    .score-warn {{ color: var(--warn); }}
    .score-bad {{ color: var(--bad); }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #f0f3f8;
      border-radius: 6px;
      padding: 12px;
      overflow-x: auto;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Qwable Lab Report</h1>
    <div class="meta">Model: <code>{html.escape(str(payload.get("model", "unknown")))}</code></div>
    <div class="meta">Generated: <code>{html.escape(generated)}</code></div>
  </header>
  <section class="summary">
    <div class="metric">Cases<strong>{summary.get("cases", 0)}</strong></div>
    <div class="metric">Avg score<strong>{summary.get("avg_score", 0)}</strong></div>
    <div class="metric">Avg latency<strong>{summary.get("avg_latency_s", 0)}s</strong></div>
  </section>
  <h2>Categories</h2>
  <ul>{categories}</ul>
  <h2>Cases</h2>
  {rows}
</main>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")


def _case_block(item: dict[str, Any]) -> str:
    score = item.get("score", {})
    ratio = float(score.get("ratio") or 0)
    score_class = "score-good" if ratio >= 0.8 else "score-warn" if ratio >= 0.5 else "score-bad"
    missing = ", ".join(score.get("missing") or []) or "none"
    violations = ", ".join(score.get("violations") or []) or "none"
    return f"""<article>
  <div class="case-head">
    <strong>{html.escape(item.get("id", "unknown"))}</strong>
    <span>{html.escape(item.get("category", ""))} · <span class="{score_class}">score {ratio}</span> · {item.get("latency_s", 0)}s</span>
  </div>
  <div class="notes">{html.escape(item.get("notes", ""))}</div>
  <h3>Prompt</h3>
  <pre><code>{html.escape(item.get("prompt", ""))}</code></pre>
  <h3>Response</h3>
  <pre><code>{html.escape(item.get("response", ""))}</code></pre>
  <p><strong>Missing:</strong> {html.escape(missing)}</p>
  <p><strong>Violations:</strong> {html.escape(violations)}</p>
</article>"""
