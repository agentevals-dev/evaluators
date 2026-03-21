"""Substring containment evaluator.

Scores each invocation 1.0 if final_response contains the configured substring,
otherwise 0.0.

Config:
  substring (str): Required for scoring; if omitted, the evaluator is a no-op (1.0).

Usage in eval_config.yaml:
    config:
      substring: "expected phrase"
"""

from __future__ import annotations

from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator


@evaluator
def contains(input: EvalInput) -> EvalResult:
    needle = (input.config.get("substring") or "").strip()
    if not needle:
        return EvalResult(
            score=1.0,
            per_invocation_scores=[1.0] * len(input.invocations),
            details={"note": "no substring configured; skipping check"},
        )

    case_insensitive = bool(input.config.get("case_insensitive", False))
    haystack_fn = str.lower if case_insensitive else lambda s: s
    needle_cmp = haystack_fn(needle)

    scores: list[float] = []
    issues: list[str] = []

    for inv in input.invocations:
        text = (inv.final_response or "")
        if case_insensitive:
            ok = needle_cmp in haystack_fn(text)
        else:
            ok = needle in text
        if ok:
            scores.append(1.0)
        else:
            scores.append(0.0)
            issues.append(f"{inv.invocation_id}: response does not contain {needle!r}")

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"issues": issues} if issues else None,
    )


if __name__ == "__main__":
    contains.run()
