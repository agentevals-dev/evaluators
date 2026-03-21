"""Expected tool call sequence evaluator.

Compares the ordered list of tool names in each invocation to config.

Config:
  expected_tool_names (list[str]): If omitted or empty, no-op (1.0).
  require_order (bool, default True): If False, compares multisets (same counts per name).

Usage:
    config:
      expected_tool_names: ["search", "calculator"]
      require_order: true
"""

from __future__ import annotations

from collections import Counter

from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator


@evaluator
def tool_sequence_match(input: EvalInput) -> EvalResult:
    expected = input.config.get("expected_tool_names")
    if not expected:
        return EvalResult(
            score=1.0,
            per_invocation_scores=[1.0] * len(input.invocations),
            details={"note": "no expected_tool_names configured; skipping check"},
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
