# time_efficiency

Scores how quickly an agent resolved relative to a time budget. Catches agents that produce correct answers but take too long for production use.

## How it works

Reads latency percentiles from the trace's `performance_metrics`. Scores against a time budget in seconds:

```
score = clamp(1.0 - actual_seconds / max_duration_s, 0, 1)
```

You choose which percentile (`p50`, `p95`, `p99`) and which latency category (`overall`, `llm_calls`, `tool_executions`) to score against. For example, scoring against `p95` of `llm_calls` catches slow LLM responses specifically.

This is a **trace-level** metric. Returns `NOT_EVALUATED` when no latency data is available or when an invalid percentile/source is configured.

## Config

| Option | Type | Default | Description |
|---|---|---|---|
| `max_duration_s` | float | 120 | Time budget in seconds |
| `latency_percentile` | str | `"p50"` | Percentile to score: `"p50"`, `"p95"`, `"p99"` |
| `latency_source` | str | `"overall"` | Latency category: `"overall"`, `"llm_calls"`, `"tool_executions"` |

## Example

```yaml
evaluators:
  - name: time_efficiency
    type: remote
    source: github
    ref: evaluators/time_efficiency/time_efficiency.py
    threshold: 0.5
    config:
      max_duration_s: 60
      latency_percentile: p95
      latency_source: overall
```

## Output details

```json
{
  "duration_s": 4.164,
  "max_duration_s": 60,
  "utilization": "6.9%",
  "source": "latency.overall.p95"
}
```

Requires `agentevals-evaluator-sdk >= 0.1.1`.
