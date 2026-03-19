# agentevals Community Evaluators

Community-maintained evaluators for [agentevals](https://github.com/agentevals-dev/agentevals) -- the agent evaluation framework built on Google ADK.

Evaluators are standalone scoring programs that evaluate agent traces. They read `EvalInput` JSON from stdin and write `EvalResult` JSON to stdout. This repository is the official index of community-contributed evaluators.

## Using community evaluators

### Browse available evaluators

```bash
agentevals evaluator list --source github
```

### Reference a community evaluator in your eval config

Add a `type: remote` entry to your `eval_config.yaml`:

```yaml
metrics:
  - tool_trajectory_avg_score

  - name: response_quality
    type: remote
    source: github
    ref: evaluators/response_quality/response_quality.py
    threshold: 0.7
    config:
      min_response_length: 20

  - name: tool_coverage
    type: remote
    source: github
    ref: evaluators/tool_coverage/tool_coverage.py
    threshold: 1.0
    config:
      min_tool_calls: 1
```

Then run as usual:

```bash
agentevals run traces/my_trace.json \
  --config eval_config.yaml \
  --eval-set eval_set.json
```

The evaluator is downloaded automatically and cached in `~/.cache/agentevals/evaluators/`.

## Contributing an evaluator

### 1. Scaffold a new evaluator

```bash
pip install agentevals
agentevals evaluator init my_evaluator
```

This creates a directory ready to be added to this repo:

```
my_evaluator/
├── my_evaluator.py     # your scoring logic
└── evaluator.yaml      # metadata manifest
```

### 2. Implement your scoring logic

Edit `my_evaluator.py`. Your function receives an `EvalInput` with the agent's invocations and returns an `EvalResult` with a score between 0.0 and 1.0.

```python
from agentevals_grader_sdk import grader, EvalInput, EvalResult

@grader
def my_evaluator(input: EvalInput) -> EvalResult:
    scores = []
    for inv in input.invocations:
        # Your scoring logic here
        scores.append(1.0)

    return EvalResult(
        score=sum(scores) / len(scores) if scores else 0.0,
        per_invocation_scores=scores,
    )

if __name__ == "__main__":
    my_evaluator.run()
```

Install the SDK standalone with `pip install agentevals-grader-sdk` (no heavy dependencies).

### 3. Update the manifest

Edit `evaluator.yaml` with a description, tags, and your name:

```yaml
name: my_evaluator
description: What this evaluator checks
language: python
entrypoint: my_evaluator.py
tags: [quality, tools]
author: your-github-username
```

### 4. Validate locally

Run the validation script to catch issues before submitting:

```bash
pip install agentevals-grader-sdk pyyaml
python scripts/validate_evaluator.py evaluators/my_evaluator
```

This checks:
- **Manifest schema** -- required fields, entrypoint exists, name matches directory
- **Syntax and imports** -- compiles cleanly, uses `@grader` decorator
- **Smoke run** -- runs the evaluator with synthetic input and validates the `EvalResult` output (correct types for `score`, `details`, `status`, etc.)

You can also test with a full eval run:

```yaml
metrics:
  - name: my_evaluator
    type: code
    path: ./evaluators/my_evaluator/my_evaluator.py
    threshold: 0.5
```

```bash
agentevals run traces/sample.json --config eval_config.yaml --eval-set eval_set.json
```

### 5. Submit a pull request

1. Fork this repository
2. Copy your evaluator directory into `evaluators/`:

```
evaluators/
├── my_evaluator/
│   ├── evaluator.yaml
│   └── my_evaluator.py
├── response_quality/
│   └── ...
└── tool_coverage/
    └── ...
```

3. Open a PR against `main`

CI will automatically validate your evaluator (manifest, syntax, and smoke run). Once merged, a separate workflow regenerates `index.yaml`, and your evaluator becomes available to everyone via `agentevals evaluator list`.

## Supported languages

Evaluators can be written in any language that reads JSON from stdin and writes JSON to stdout.

| Language | Extension | SDK available |
|---|---|---|
| Python | `.py` | `pip install agentevals-grader-sdk` |
| JavaScript | `.js` | No SDK yet -- just read stdin, write stdout |
| TypeScript | `.ts` | No SDK yet -- just read stdin, write stdout |

See the [custom evaluators documentation](https://github.com/agentevals-dev/agentevals/blob/main/docs/custom-evaluators.md) for the full protocol reference.
