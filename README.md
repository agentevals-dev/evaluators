# agentevals Community Graders

Community-maintained graders for [agentevals](https://github.com/agentevals-dev/agentevals) -- the agent evaluation framework built on Google ADK.

Graders are standalone scoring programs that evaluate agent traces. They read `EvalInput` JSON from stdin and write `EvalResult` JSON to stdout. This repository is the official index of community-contributed graders.

## Using community graders

### Browse available graders

```bash
agentevals grader list --source github
```

### Reference a community grader in your eval config

Add a `type: remote` entry to your `eval_config.yaml`:

```yaml
metrics:
  - tool_trajectory_avg_score

  - name: response_quality
    type: remote
    source: github
    ref: graders/response_quality/response_quality.py
    threshold: 0.7
    config:
      min_response_length: 20

  - name: tool_coverage
    type: remote
    source: github
    ref: graders/tool_coverage/tool_coverage.py
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

The grader is downloaded automatically and cached in `~/.cache/agentevals/graders/`.

## Contributing a grader

### 1. Scaffold a new grader

```bash
pip install agentevals
agentevals grader init my_grader
```

This creates a directory ready to be added to this repo:

```
my_grader/
├── my_grader.py     # your scoring logic
└── grader.yaml      # metadata manifest
```

### 2. Implement your scoring logic

Edit `my_grader.py`. Your function receives an `EvalInput` with the agent's invocations and returns an `EvalResult` with a score between 0.0 and 1.0.

```python
from agentevals_grader_sdk import grader, EvalInput, EvalResult

@grader
def my_grader(input: EvalInput) -> EvalResult:
    scores = []
    for inv in input.invocations:
        # Your scoring logic here
        scores.append(1.0)

    return EvalResult(
        score=sum(scores) / len(scores) if scores else 0.0,
        per_invocation_scores=scores,
    )
```

Install the SDK standalone with `pip install agentevals-grader-sdk` (no heavy dependencies).

### 3. Update the manifest

Edit `grader.yaml` with a description, tags, and your name:

```yaml
name: my_grader
description: What this grader checks
language: python
entrypoint: my_grader.py
tags: [quality, tools]
author: your-github-username
```

### 4. Test locally

Add it to an eval config as a local `type: code` grader and run it:

```yaml
metrics:
  - name: my_grader
    type: code
    path: ./my_grader/my_grader.py
    threshold: 0.5
```

```bash
agentevals run traces/sample.json --config eval_config.yaml --eval-set eval_set.json
```

### 5. Submit a pull request

1. Fork this repository
2. Copy your grader directory into `graders/`:

```
graders/
├── my_grader/
│   ├── grader.yaml
│   └── my_grader.py
├── response_quality/
│   └── ...
└── tool_coverage/
    └── ...
```

3. Open a PR against `main`

A CI workflow will validate your `grader.yaml` manifest. Once merged, the workflow regenerates `index.yaml` automatically, and your grader becomes available to everyone via `agentevals grader list`.

## Supported languages

Graders can be written in any language that reads JSON from stdin and writes JSON to stdout.

| Language | Extension | SDK available |
|---|---|---|
| Python | `.py` | `pip install agentevals-grader-sdk` |
| JavaScript | `.js` | No SDK yet -- just read stdin, write stdout |
| TypeScript | `.ts` | No SDK yet -- just read stdin, write stdout |

See the [custom graders documentation](https://github.com/agentevals-dev/agentevals/blob/main/docs/custom-graders.md) for the full protocol reference.
