"""Regex on final response evaluator.

Config:
  pattern (str): If omitted, no-op (1.0).
  flags (str, optional): "IGNORECASE" | "MULTILINE" | "DOTALL" — combined with |.

Usage:
    config:
      pattern: "^The answer"
      flags: IGNORECASE
"""

from __future__ import annotations

import re

from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator

_FLAG_MAP = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
}


@evaluator
def regex_match(input: EvalInput) -> EvalResult:
    pattern = input.config.get("pattern")
    if not pattern:
        return EvalResult(
            score=1.0,
            per_invocation_scores=[1.0] * len(input.invocations),
            details={"note": "no pattern configured; skipping check"},
        )

    flag_names = input.config.get("flags")
    flags = 0
    if isinstance(flag_names, str):
        for part in flag_names.replace("|", ",").split(","):
            key = part.strip().upper()
            if key in _FLAG_MAP:
                flags |= _FLAG_MAP[key]
    elif isinstance(flag_names, list):
        for part in flag_names:
            key = str(part).strip().upper()
            if key in _FLAG_MAP:
                flags |= _FLAG_MAP[key]

    try:
        rx = re.compile(str(pattern), flags)
    except re.error as exc:
        return EvalResult(
            score=0.0,
            per_invocation_scores=[0.0] * len(input.invocations),
            details={"error": f"invalid regex: {exc}"},
        )

    scores: list[float] = []
    issues: list[str] = []

    for inv in input.invocations:
        text = inv.final_response or ""
        if rx.search(text):
            scores.append(1.0)
        else:
            scores.append(0.0)
            issues.append(f"{inv.invocation_id}: no match for pattern {pattern!r}")

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"issues": issues} if issues else None,
    )


if __name__ == "__main__":
    regex_match.run()
