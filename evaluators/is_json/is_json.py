"""JSON parse check evaluator.

Tries to parse final_response as JSON. Optionally extracts fenced ```json ... ``` blocks.

Config:
  extract_markdown_fence (bool, default True): Strip ```json fences if present.

Usage:
    config:
      extract_markdown_fence: true
"""

from __future__ import annotations

import json
import re

from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator

_FENCE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL | re.IGNORECASE)


def _parse_json_payload(text: str, extract_fence: bool) -> object:
    raw = (text or "").strip()
    if extract_fence:
        m = _FENCE.match(raw)
        if m:
            raw = m.group(1).strip()
    return json.loads(raw)


@evaluator
def is_json(input: EvalInput) -> EvalResult:
    extract_fence = bool(input.config.get("extract_markdown_fence", True))

    scores: list[float] = []
    issues: list[str] = []

    for inv in input.invocations:
        try:
            _parse_json_payload(inv.final_response or "", extract_fence)
            scores.append(1.0)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            scores.append(0.0)
            issues.append(f"{inv.invocation_id}: not valid JSON ({exc})")

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"issues": issues} if issues else None,
    )


if __name__ == "__main__":
    is_json.run()
