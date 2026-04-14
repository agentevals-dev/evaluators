# token_efficiency

Scores how efficiently an agent used tokens relative to a budget. Useful for catching runaway token consumption — real benchmarks show 8x variation across agent solutions for the same task.

## How it works

Reads token counts from the trace's `performance_metrics`. Scores input and output tokens separately against their budgets, returns the worst of the two:

```
input_score  = clamp(1.0 - input_tokens / max_input_tokens,  0, 1)
output_score = clamp(1.0 - output_tokens / max_output_tokens, 0, 1)
score = min(input_score, output_score)
```

A score of 1.0 means zero tokens used; 0.0 means at or over budget. With a threshold of 0.3, the agent must use less than 70% of the budget to pass.

This is a **trace-level** metric — per-invocation scores are not applicable (token counts come from the full trace).

Returns `NOT_EVALUATED` when no token data is available in the trace.

## Config

| Option | Type | Default | Description |
|---|---|---|---|
| `max_input_tokens` | int | 150000 | Input (prompt) token budget |
| `max_output_tokens` | int | 50000 | Output (completion) token budget |

## Example

```yaml
evaluators:
  - name: token_efficiency
    type: remote
    source: github
    ref: evaluators/token_efficiency/token_efficiency.py
    threshold: 0.3
    config:
      max_input_tokens: 100000
      max_output_tokens: 30000
```

## Output details

```json
{
  "input_tokens": 75000,
  "output_tokens": 10000,
  "max_input_tokens": 100000,
  "max_output_tokens": 30000,
  "input_utilization": "75.0%",
  "output_utilization": "33.3%",
  "input_score": 0.25,
  "output_score": 0.6667
}
```

Requires `agentevals-evaluator-sdk >= 0.1.1`.
