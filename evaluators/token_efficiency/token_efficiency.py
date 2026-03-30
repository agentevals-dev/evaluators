"""Community evaluator: token_efficiency

Scores token usage relative to a budget. Extracts input/output tokens from
performance_metrics when available, otherwise returns NOT_EVALUATED.

Config: max_tokens (int, default 200000), weight_input (float, default 0.7),
        weight_output (float, default 0.3)
"""

from agentevals_evaluator_sdk import EvalInput, EvalResult, EvalStatus, evaluator


def _extract_tokens(inv) -> dict | None:
    perf = getattr(inv, "performance_metrics", None)
    if perf is None and hasattr(inv, "__getitem__"):
        try:
            perf = inv["performance_metrics"]
        except (KeyError, TypeError):
            perf = None

    if isinstance(perf, dict):
        input_t = perf.get("input_tokens") or perf.get("prompt_tokens")
        output_t = perf.get("output_tokens") or perf.get("completion_tokens")
        if input_t is not None or output_t is not None:
            return {"input_tokens": int(input_t or 0), "output_tokens": int(output_t or 0)}

    return None


@evaluator
def token_efficiency(input: EvalInput) -> EvalResult:
    max_tokens = input.config.get("max_tokens", 200000)
    weight_input = input.config.get("weight_input", 0.7)
    weight_output = input.config.get("weight_output", 0.3)

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
        weighted = (tokens["input_tokens"] * weight_input) + (tokens["output_tokens"] * weight_output)
        score = max(0.0, min(1.0, 1.0 - (weighted / max_tokens)))
        scores.append(score)
        details_items.append(
            f"{inv.invocation_id}: {tokens['input_tokens']}in + {tokens['output_tokens']}out "
            f"(weighted {weighted:.0f}/{max_tokens})"
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
