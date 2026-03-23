"""Expected tool call sequence evaluator.

Compares the ordered list of tool names in each invocation to config.

Config:
  expected_tool_names (list[str]): Required non-empty. Otherwise returns NOT_EVALUATED.
  require_order (bool, default True): If False, compares multisets (same counts per name).

Usage:
    config:
      expected_tool_names: ["search", "calculator"]
      require_order: true
"""

from __future__ import annotations

from collections import Counter

from agentevals_evaluator_sdk import EvalInput, EvalResult, EvalStatus, evaluator


@evaluator
def tool_sequence_match(input: EvalInput) -> EvalResult:
    expected = input.config.get("expected_tool_names")
    n = len(input.invocations)
    if expected is None or not isinstance(expected, list):
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": "missing or invalid config: expected_tool_names (need a list of names)"},
        )
    if not expected:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": "missing or empty config: expected_tool_names"},
        )

    want = [str(x) for x in expected]
    require_order = bool(input.config.get("require_order", True))

    scores: list[float] = []
    issues: list[str] = []

    for inv in input.invocations:
        actual = []
        for call in inv.intermediate_steps.tool_calls or []:
            if isinstance(call, dict):
                n = call.get("name")
                if n is not None:
                    actual.append(str(n))

        if require_order:
            ok = actual == want
        else:
            ok = Counter(actual) == Counter(want)

        if ok:
            scores.append(1.0)
        else:
            scores.append(0.0)
            issues.append(
                f"{inv.invocation_id}: expected {want!r}, got {actual!r} "
                f"(require_order={require_order})"
            )

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"issues": issues} if issues else None,
    )


if __name__ == "__main__":
    tool_sequence_match.run()
