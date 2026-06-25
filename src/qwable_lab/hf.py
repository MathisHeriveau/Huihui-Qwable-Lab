from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen


REPO_ID = "huihui-ai/Huihui-Qwable-3.6-27b-abliterated-MTP-GGUF"
API_URL = f"https://huggingface.co/api/models/{REPO_ID}"


@dataclass(frozen=True)
class ModelFile:
    name: str
    size: int | None = None

    @property
    def size_gb(self) -> str:
        if self.size is None:
            return "unknown"
        return f"{self.size / 1024**3:.2f} GiB"


@dataclass(frozen=True)
class ModelInfo:
    repo_id: str
    sha: str | None
    last_modified: str | None
    downloads: int | None
    likes: int | None
    license: str | None
    tags: list[str]
    context_length: int | None
    architecture: str | None
    files: list[ModelFile]


def fetch_model_info(timeout: int = 30) -> ModelInfo:
    req = Request(API_URL, headers={"User-Agent": "qwable-lab/0.1"})
    with urlopen(req, timeout=timeout) as response:
        payload: dict[str, Any] = json.load(response)

    gguf = payload.get("gguf") or {}
    card = payload.get("cardData") or {}
    files = []
    for sibling in payload.get("siblings", []):
        name = sibling.get("rfilename")
        if not isinstance(name, str) or not name.endswith(".gguf"):
            continue
        size = None
        lfs = sibling.get("lfs")
        if isinstance(lfs, dict) and isinstance(lfs.get("size"), int):
            size = lfs["size"]
        files.append(ModelFile(name=name, size=size))

    return ModelInfo(
        repo_id=payload.get("modelId") or REPO_ID,
        sha=payload.get("sha"),
        last_modified=payload.get("lastModified"),
        downloads=payload.get("downloads"),
        likes=payload.get("likes"),
        license=card.get("license"),
        tags=list(payload.get("tags") or []),
        context_length=gguf.get("context_length"),
        architecture=gguf.get("architecture"),
        files=files,
    )


def choose_quant_file(info: ModelInfo, quant: str) -> ModelFile:
    quant_lower = quant.lower()
    candidates = [
        file for file in info.files
        if quant_lower in file.name.lower() and "mmproj" not in file.name.lower()
    ]
    if not candidates:
        available = ", ".join(file.name for file in info.files) or "none"
        raise ValueError(f"No GGUF file matched {quant!r}. Available: {available}")
    return candidates[0]


def find_mmproj(info: ModelInfo) -> ModelFile | None:
    for file in info.files:
        if "mmproj" in file.name.lower():
            return file
    return None
