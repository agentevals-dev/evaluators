"""Normalized Levenshtein similarity evaluator.

Score for an invocation is 1.0 - (edit_distance / max(len(a), len(b), 1)), clamped to [0, 1].

Config:
  expected (str): If omitted, no-op (1.0).
  case_insensitive (bool, default False): Compare lowercased strings.

Usage:
    config:
      expected: "reference answer"
"""

from __future__ import annotations

from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator


def _levenshtein(a: str, b: str) -> int:
    """Classic O(nm) edit distance."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        cur = [i + 1]
        for j, cb in enumerate(b):
            ins = prev[j + 1] + 1
            delete = cur[j] + 1
            sub = prev[j] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


@evaluator
def levenshtein_ratio(input: EvalInput) -> EvalResult:
    expected = input.config.get("expected")
    if expected is None:
        return EvalResult(
            score=1.0,
            per_invocation_scores=[1.0] * len(input.invocations),
            details={"note": "no expected string configured; skipping check"},
        )

    case_insensitive = bool(input.config.get("case_insensitive", False))
    ref = str(expected)
    if case_insensitive:
        ref = ref.lower()

    scores: list[float] = []
    details_rows: list[dict] = []

    for inv in input.invocations:
        got = inv.final_response or ""
        a, b = (got.lower(), ref) if case_insensitive else (got, ref)
        dist = _levenshtein(a, b)
        denom = max(len(a), len(b), 1)
        sim = 1.0 - (dist / denom)
        sim = max(0.0, min(1.0, sim))
        scores.append(sim)
        details_rows.append(
            {
                "invocation_id": inv.invocation_id,
                "distance": dist,
                "similarity": sim,
            }
        )

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"per_invocation": details_rows},
    )


if __name__ == "__main__":
    levenshtein_ratio.run()
