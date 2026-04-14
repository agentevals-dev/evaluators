"""Community evaluator: token_efficiency

Scores token usage relative to a budget.  Reads token counts from
the trace's performance_metrics.

Score formula (per dimension):
  input_score  = clamp(1.0 - total_prompt / max_input_tokens,  0, 1)
  output_score = clamp(1.0 - total_output / max_output_tokens, 0, 1)
  score = min(input_score, output_score)

Returns NOT_EVALUATED when no token data is available.

Config options:
  max_input_tokens  (int): Input token budget  (default: 150000)
  max_output_tokens (int): Output token budget  (default: 50000)
"""

from __future__ import annotations

from agentevals_evaluator_sdk import EvalInput, EvalResult, EvalStatus, evaluator


def _extract_tokens(perf: dict) -> dict[str, int] | None:
    """Extract token counts from a performance_metrics dict.

    Supports two layouts:
      nested (agentevals default): {"tokens": {"total_prompt": N, "total_output": N}}
      flat   (custom harness):     {"input_tokens": N, "output_tokens": N}
    """
    tokens_block = perf.get("tokens")
    if isinstance(tokens_block, dict):
        total_prompt = tokens_block.get("total_prompt")
        total_output = tokens_block.get("total_output")
        if total_prompt is not None or total_output is not None:
            return {
                "input_tokens": int(total_prompt) if total_prompt is not None else 0,
                "output_tokens": int(total_output) if total_output is not None else 0,
            }

    input_t = perf.get("input_tokens")
    if input_t is None:
        input_t = perf.get("prompt_tokens")
    output_t = perf.get("output_tokens")
    if output_t is None:
        output_t = perf.get("completion_tokens")

    if input_t is not None or output_t is not None:
        return {
            "input_tokens": int(input_t) if input_t is not None else 0,
            "output_tokens": int(output_t) if output_t is not None else 0,
        }

    return None


def _get_perf(input: EvalInput) -> dict | None:
    """Return the first non-None performance_metrics from any invocation."""
    for inv in input.invocations:
        if isinstance(inv.performance_metrics, dict):
            return inv.performance_metrics
    return None


@evaluator
def token_efficiency(input: EvalInput) -> EvalResult:
    max_input = input.config.get("max_input_tokens", 150_000)
    max_output = input.config.get("max_output_tokens", 50_000)
    n = len(input.invocations)

    perf = _get_perf(input)
    if perf is None:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": "no performance_metrics available"},
        )

    tokens = _extract_tokens(perf)
    if tokens is None:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": "no token data in performance_metrics"},
        )

    input_tokens = tokens["input_tokens"]
    output_tokens = tokens["output_tokens"]

    input_score = max(0.0, min(1.0, 1.0 - input_tokens / max_input)) if max_input > 0 else 1.0
    output_score = max(0.0, min(1.0, 1.0 - output_tokens / max_output)) if max_output > 0 else 1.0
    score = min(input_score, output_score)

    return EvalResult(
        score=score,
        per_invocation_scores=[None] * n,
        details={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "max_input_tokens": max_input,
            "max_output_tokens": max_output,
            "input_utilization": f"{input_tokens / max_input * 100:.1f}%" if max_input > 0 else "n/a",
            "output_utilization": f"{output_tokens / max_output * 100:.1f}%" if max_output > 0 else "n/a",
            "input_score": round(input_score, 4),
            "output_score": round(output_score, 4),
        },
    )


if __name__ == "__main__":
    token_efficiency.run()
