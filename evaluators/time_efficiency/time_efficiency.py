"""Community evaluator: time_efficiency

Scores resolution time relative to a budget.  Reads latency from
the trace's performance_metrics.

Score = clamp(1.0 - actual_seconds / max_duration_s, 0, 1)

Returns NOT_EVALUATED when no latency data is available.

Config options:
  max_duration_s       (float): Time budget in seconds (default: 120)
  latency_percentile   (str):   Which percentile to score against:
                                "p50" (default), "p95", "p99"
  latency_source       (str):   Latency category:
                                "overall" (default), "llm_calls", "tool_executions"
"""

from __future__ import annotations

from agentevals_evaluator_sdk import EvalInput, EvalResult, EvalStatus, evaluator

_VALID_PERCENTILES = ("p50", "p95", "p99")
_VALID_SOURCES = ("overall", "llm_calls", "tool_executions")


def _extract_duration_s(perf: dict, percentile: str, source: str) -> tuple[float | None, str]:
    """Extract duration in seconds from a performance_metrics dict.

    Returns (duration_seconds, description_of_source).

    Supports:
      nested (agentevals): latency.<source>.<percentile> in milliseconds
      flat:                duration_s (seconds) or duration_ms (milliseconds)
    """
    latency_block = perf.get("latency")
    if isinstance(latency_block, dict):
        source_block = latency_block.get(source)
        if isinstance(source_block, dict):
            ms_value = source_block.get(percentile)
            if ms_value is not None:
                return float(ms_value) / 1000.0, f"latency.{source}.{percentile}"

    duration_s = perf.get("duration_s")
    if duration_s is not None:
        return float(duration_s), "duration_s"

    duration_ms = perf.get("duration_ms")
    if duration_ms is not None:
        return float(duration_ms) / 1000.0, "duration_ms"

    return None, "no latency data found"


def _get_perf(input: EvalInput) -> dict | None:
    """Return the first non-None performance_metrics from any invocation."""
    for inv in input.invocations:
        if isinstance(inv.performance_metrics, dict):
            return inv.performance_metrics
    return None


@evaluator
def time_efficiency(input: EvalInput) -> EvalResult:
    max_duration = input.config.get("max_duration_s", 120.0)
    percentile = input.config.get("latency_percentile", "p50")
    source = input.config.get("latency_source", "overall")
    n = len(input.invocations)

    if percentile not in _VALID_PERCENTILES:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": f"invalid latency_percentile '{percentile}', must be one of {_VALID_PERCENTILES}"},
        )
    if source not in _VALID_SOURCES:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": f"invalid latency_source '{source}', must be one of {_VALID_SOURCES}"},
        )

    perf = _get_perf(input)
    if perf is None:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": "no performance_metrics available"},
        )

    duration_s, source_desc = _extract_duration_s(perf, percentile, source)
    if duration_s is None:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": source_desc},
        )

    score = max(0.0, min(1.0, 1.0 - duration_s / max_duration)) if max_duration > 0 else 1.0

    breakdown = {}
    latency_block = perf.get("latency")
    if isinstance(latency_block, dict):
        for src in _VALID_SOURCES:
            src_block = latency_block.get(src)
            if isinstance(src_block, dict):
                val = src_block.get(percentile)
                if val is not None:
                    breakdown[src] = round(float(val) / 1000.0, 3)

    details: dict = {
        "duration_s": round(duration_s, 3),
        "max_duration_s": max_duration,
        "utilization": f"{duration_s / max_duration * 100:.1f}%" if max_duration > 0 else "n/a",
        "source": source_desc,
    }
    if breakdown:
        details["latency_breakdown_s"] = breakdown

    return EvalResult(
        score=score,
        per_invocation_scores=[None] * n,
        details=details,
    )


if __name__ == "__main__":
    time_efficiency.run()
