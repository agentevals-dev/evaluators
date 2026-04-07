"""Community evaluator: token_efficiency

Scores token usage relative to a budget. Extracts input/output tokens from
performance_metrics when available, otherwise returns NOT_EVALUATED.

Config: max_input_tokens (int, default 150000), max_output_tokens (int, default 50000)
"""

from agentevals_evaluator_sdk import EvalInput, EvalResult, EvalStatus, evaluator


def _extract_tokens(inv) -> dict | None:
    perf = inv.performance_metrics
    if not isinstance(perf, dict):
        return None

    input_t = perf.get("input_tokens") or perf.get("prompt_tokens")
    output_t = perf.get("output_tokens") or perf.get("completion_tokens")
    if input_t is not None or output_t is not None:
        return {"input_tokens": int(input_t or 0), "output_tokens": int(output_t or 0)}

    return None


@evaluator
def token_efficiency(input: EvalInput) -> EvalResult:
    max_input = input.config.get("max_input_tokens", 150000)
    max_output = input.config.get("max_output_tokens", 50000)

    scores: list[float] = []
    details_items: list[str] = []
    has_data = False

    for inv in input.invocations:
        tokens = _extract_tokens(inv)
        if tokens is None:
            scores.append(0.0)
            details_items.append(f"{inv.invocation_id}: no token data")
            continue

        has_data = True
        input_score = max(0.0, min(1.0, 1.0 - (tokens["input_tokens"] / max_input))) if max_input > 0 else 1.0
        output_score = max(0.0, min(1.0, 1.0 - (tokens["output_tokens"] / max_output))) if max_output > 0 else 1.0
        score = min(input_score, output_score)
        scores.append(score)
        details_items.append(
            f"{inv.invocation_id}: {tokens['input_tokens']}in/{max_input} + "
            f"{tokens['output_tokens']}out/{max_output} -> {score:.2f}"
        )

    if not has_data:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            details={"reason": "no token data in any invocation"},
        )

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(score=overall, per_invocation_scores=scores, details={"token_details": details_items})


if __name__ == "__main__":
    token_efficiency.run()
