"""Community evaluator: time_efficiency

Scores how quickly the agent resolved relative to a time budget.
Uses performance_metrics.duration_s from trace data when available.

Config options:
  max_duration_s (float): Time budget in seconds (default: 120)
"""

from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator


def _extract_duration(inv) -> float | None:
    """Extract duration_s from an invocation's performance_metrics."""
    perf = getattr(inv, "performance_metrics", None)
    if perf is None and hasattr(inv, "__getitem__"):
        try:
            perf = inv["performance_metrics"]
        except (KeyError, TypeError):
            perf = None

    if isinstance(perf, dict):
        duration = perf.get("duration_s") or perf.get("duration")
        if duration is not None:
            return float(duration)

    return None


@evaluator
def time_efficiency(input: EvalInput) -> EvalResult:
    max_duration = input.config.get("max_duration_s", 120.0)

    scores: list[float] = []
    details_items: list[str] = []
    has_data = False

    for inv in input.invocations:
        duration = _extract_duration(inv)

        if duration is None:
            # No timing data — assign neutral score
            scores.append(0.5)
            details_items.append(f"{inv.invocation_id}: no duration data available")
            continue

        has_data = True
        score = max(0.0, min(1.0, 1.0 - (duration / max_duration)))
        scores.append(score)
        details_items.append(
            f"{inv.invocation_id}: {duration:.1f}s / {max_duration:.1f}s budget (score: {score:.2f})"
        )

    overall = sum(scores) / len(scores) if scores else 0.0

    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={
            "time_details": details_items,
            "has_trace_data": has_data,
            "max_duration_s": max_duration,
        },
    )


if __name__ == "__main__":
    time_efficiency.run()
