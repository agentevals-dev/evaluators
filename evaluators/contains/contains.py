"""Substring containment evaluator.

Scores each invocation 1.0 if final_response contains the configured substring,
otherwise 0.0.

Config:
  substring (str): Required. If omitted, returns NOT_EVALUATED.

Usage in eval_config.yaml:
    config:
      substring: "expected phrase"
"""

from __future__ import annotations

from agentevals_evaluator_sdk import EvalInput, EvalResult, EvalStatus, evaluator


@evaluator
def contains(input: EvalInput) -> EvalResult:
    substring = (input.config.get("substring") or "").strip()
    n = len(input.invocations)
    if not substring:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": "missing config: substring"},
        )

    case_insensitive = bool(input.config.get("case_insensitive", False))
    normalize = str.lower if case_insensitive else lambda s: s
    substring_cmp = normalize(substring)

    scores: list[float] = []
    issues: list[str] = []

    for inv in input.invocations:
        response_text = inv.final_response or ""
        if case_insensitive:
            ok = substring_cmp in normalize(response_text)
        else:
            ok = substring in response_text
        if ok:
            scores.append(1.0)
        else:
            scores.append(0.0)
            issues.append(f"{inv.invocation_id}: response does not contain {substring!r}")

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"issues": issues} if issues else None,
    )


if __name__ == "__main__":
    contains.run()
