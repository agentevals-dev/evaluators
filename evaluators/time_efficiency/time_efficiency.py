"""Community evaluator: time_efficiency

Scores resolution time relative to a budget. Extracts duration_s from
performance_metrics when available, otherwise returns NOT_EVALUATED.

Config: max_duration_s (float, default 120)
"""

from agentevals_evaluator_sdk import EvalInput, EvalResult, EvalStatus, evaluator


def _extract_duration(inv) -> float | None:
    perf = getattr(inv, "performance_metrics", None)
    if perf is None and hasattr(inv, "__getitem__"):
        try:
            perf = inv["performance_metrics"]
        except (KeyError, TypeError):
            perf = None

    if isinstance(perf, dict):
        d = perf.get("duration_s") or perf.get("duration")
        if d is not None:
            return float(d)
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
            scores.append(0.0)
            details_items.append(f"{inv.invocation_id}: no duration data")
            continue

        has_data = True
        score = max(0.0, min(1.0, 1.0 - (duration / max_duration)))
        scores.append(score)
        details_items.append(f"{inv.invocation_id}: {duration:.1f}s / {max_duration:.1f}s")

    if not has_data:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            details={"reason": "no duration data in any invocation"},
        )

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(score=overall, per_invocation_scores=scores, details={"time_details": details_items})


if __name__ == "__main__":
    time_efficiency.run()
