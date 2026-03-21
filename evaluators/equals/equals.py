"""Exact string match evaluator.

Config:
  expected (str): If omitted, no-op (1.0).
  case_insensitive (bool, default True): Compare normalized strings.
  strip (bool, default True): Strip whitespace before compare.

Usage:
    config:
      expected: "4"
"""

from __future__ import annotations

from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator


@evaluator
def equals(input: EvalInput) -> EvalResult:
    expected = input.config.get("expected")
    if expected is None:
        return EvalResult(
            score=1.0,
            per_invocation_scores=[1.0] * len(input.invocations),
            details={"note": "no expected string configured; skipping check"},
        )

    case_insensitive = bool(input.config.get("case_insensitive", True))
    strip = bool(input.config.get("strip", True))

    def norm(s: str) -> str:
        t = s.strip() if strip else s
        return t.lower() if case_insensitive else t

    exp = norm(str(expected))
    scores: list[float] = []
    issues: list[str] = []

    for inv in input.invocations:
        got = norm(inv.final_response or "")
        if got == exp:
            scores.append(1.0)
        else:
            scores.append(0.0)
            issues.append(
                f"{inv.invocation_id}: expected {expected!r}, got {inv.final_response!r}"
            )

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"issues": issues} if issues else None,
    )


if __name__ == "__main__":
    equals.run()
