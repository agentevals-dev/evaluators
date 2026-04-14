# tool_efficiency

Scores whether an agent used tools effectively. Catches waste: duplicate calls (same tool + same args), error responses, and exceeding a tool call budget. Also enforces a minimum number of tool calls when tools are required.

## How it works

Scores each invocation independently based on three factors multiplied together:

```
useful_calls = total - duplicates - errors
efficiency   = useful_calls / total
budget_factor = clamp(1.0 - max(0, total - max_tool_calls) / max_tool_calls, 0, 1)
min_factor    = total / min_tool_calls   (when total < min_tool_calls)
score = clamp(efficiency * budget_factor * min_factor, 0, 1)
```

- **efficiency**: What fraction of calls were useful (not duplicates, not errors).
- **budget_factor**: Penalizes exceeding `max_tool_calls`. At 2x budget, score goes to 0.
- **min_factor**: Penalizes falling below `min_tool_calls`. 1 call when 2 are required = 0.5x.

If an invocation has zero tool calls: score is 0.0 when `min_tool_calls > 0`, otherwise 1.0.

The overall score is the mean across invocations.

**Duplicate detection**: Two calls are duplicates if they have the same tool name and identical arguments (JSON-serialized, sorted keys).

**Error detection**: Checks `ToolResponseData.status` for `"error"`, `"failed"`, or `"failure"`.

## Config

| Option | Type | Default | Description |
|---|---|---|---|
| `max_tool_calls` | int | 15 | Budget; calls beyond this are penalized |
| `min_tool_calls` | int | 0 | Minimum required; 0 means tools are optional |
| `penalize_duplicates` | bool | true | Count duplicate calls as waste |
| `penalize_errors` | bool | true | Count error responses as waste |

## Example

```yaml
evaluators:
  - name: tool_efficiency
    type: remote
    source: github
    ref: evaluators/tool_efficiency/tool_efficiency.py
    threshold: 0.5
    config:
      max_tool_calls: 10
      min_tool_calls: 1
      penalize_duplicates: true
      penalize_errors: true
```

## Output details

```json
{
  "per_invocation": [
    {
      "invocation_id": "inv-001",
      "score": 0.3429,
      "total_calls": 7,
      "useful_calls": 4,
      "duplicate_calls": 2,
      "error_responses": 1,
      "budget_factor": 0.6
    }
  ]
}
```

Requires `agentevals-evaluator-sdk >= 0.1.1`.
