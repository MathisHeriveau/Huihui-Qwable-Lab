# Huihui Qwable Lab

A small local evaluation lab for `huihui-ai/Huihui-Qwable-3.6-27b-abliterated-MTP-GGUF`.

It does three things:

- fetches current Hugging Face metadata for the GGUF repo;
- runs editable prompts against an OpenAI-compatible local endpoint;
- writes JSON and HTML reports so you can compare runs.

The project does not download the 27B weights automatically. Pick the GGUF file you want, start a local server, then point this lab at it.

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .

qwable-lab models
```

Download the GGUF files first. Use `hf download` with explicit filenames; this is more reliable than `--include` for this repo.

```bash
hf download \
  huihui-ai/Huihui-Qwable-3.6-27b-abliterated-MTP-GGUF \
  Huihui-Qwable-3.6-27b-abliterated-Q4_K_M_Q8-MTP.gguf \
  --local-dir models/qwable

hf download \
  huihui-ai/Huihui-Qwable-3.6-27b-abliterated-MTP-GGUF \
  mmproj-model-f16.gguf \
  --local-dir models/qwable
```

Start a local OpenAI-compatible server:

```bash
./bin/llama-server \
  -m models/qwable/Huihui-Qwable-3.6-27b-abliterated-Q4_K_M_Q8-MTP.gguf \
  --mmproj models/qwable/mmproj-model-f16.gguf \
  --jinja \
  -c 32768 \
  -ngl 0 \
  --host 127.0.0.1 \
  --port 8080
```

Do not use `-hf` with the local CPU build unless it was compiled with HTTPS support. The bundled build intentionally expects files downloaded by `hf download`.

Then run the lab:

```bash
qwable-lab smoke --endpoint http://127.0.0.1:8080/v1
qwable-lab run \
  --endpoint http://127.0.0.1:8080/v1 \
  --model local-qwable \
  --scenario scenarios/default.jsonl \
  --out runs/qwable-default.json
qwable-lab report --run runs/qwable-default.json --out reports/qwable-default.html
```

Open `reports/qwable-default.html` in a browser.

## Compare Another Model

Run the same scenario against any OpenAI-compatible endpoint:

```bash
qwable-lab run \
  --endpoint http://127.0.0.1:11434/v1 \
  --model qwen3:latest \
  --scenario scenarios/default.jsonl \
  --out runs/qwen3-default.json
```

Generate another report, or inspect the JSON side by side.

## Scenario Format

Each line in `scenarios/default.jsonl` is one case:

```json
{"id":"reasoning-01","category":"reasoning","prompt":"...","checks":{"must_include":["..."],"must_avoid":["..."]}}
```

Supported fields:

- `id`: stable case id.
- `category`: free-form grouping.
- `system`: optional system instruction.
- `prompt`: user prompt.
- `temperature`: optional override.
- `max_tokens`: optional override.
- `checks.must_include`: simple keyword checks.
- `checks.must_avoid`: simple keyword checks.
- `notes`: what to look for during manual review.

The automatic score is deliberately simple. Treat it as a triage signal, not a benchmark truth.

## Commands

```bash
qwable-lab models
qwable-lab download-command --quant Q4_K_M_Q8
qwable-lab smoke --endpoint http://127.0.0.1:8080/v1
qwable-lab run --endpoint http://127.0.0.1:8080/v1 --model local-qwable
qwable-lab report --run runs/latest.json
```

## Local llama.cpp Build

If `llama-server` is not installed globally, build it inside this project:

```bash
git clone --depth 1 https://github.com/ggml-org/llama.cpp tools/llama.cpp
cmake -S tools/llama.cpp -B tools/llama.cpp/build -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF
cmake --build tools/llama.cpp/build --config Release --target llama-server -j 4
./bin/llama-server --version
```

This CPU build is mainly a compatibility baseline. For good 27B performance, use a GPU-enabled llama.cpp build or another OpenAI-compatible runtime. If you rebuild `llama.cpp` with GPU support, change `-ngl 0` to `-ngl 99` or `-ngl auto`.

## Notes

- The model is large. Expect memory pressure even in 4-bit quantization.
- MTP support depends on your runtime. The lab measures behavior through the API; it does not verify internal speculative decoding.
- Multimodal support depends on the server, chat template, and projector wiring. This lab starts with text-only tests so the baseline is repeatable.
