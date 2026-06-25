# Evaluation Playbook

Use this checklist when you want to decide whether the model is actually good for your work.

## 1. Freeze the Runtime

Record:

- GGUF filename and quantization;
- runtime name and version;
- context size;
- GPU offload setting;
- temperature and max token settings;
- whether MTP/speculative decoding is enabled by the runtime.

## 2. Run the Baseline

```bash
qwable-lab run \
  --endpoint http://127.0.0.1:8080/v1 \
  --model local-qwable \
  --scenario scenarios/default.jsonl \
  --out runs/qwable-default.json

qwable-lab report \
  --run runs/qwable-default.json \
  --out reports/qwable-default.html
```

## 3. Compare Against a Control Model

Keep the same scenario and sampling settings:

```bash
qwable-lab run \
  --endpoint http://127.0.0.1:11434/v1 \
  --model qwen-control \
  --scenario scenarios/default.jsonl \
  --out runs/control-default.json
```

## 4. Manual Review Rubric

Score each answer from 1 to 5:

- correctness: does it solve the task;
- instruction following: does it obey format and constraints;
- calibration: does it admit uncertainty instead of inventing facts;
- usefulness: would you keep the answer with light editing;
- safety boundary: does it follow safe redirection when explicitly asked.

The keyword score in the HTML report is only a smoke signal. Your manual rubric is the real evaluation.

## 5. Add Your Own Cases

Copy `scenarios/default.jsonl` and add prompts from your actual workload. Good cases are small, specific, and easy to judge. Include one or two traps you have seen models fail before.
