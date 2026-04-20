"""Skills trajectory evaluator.

Scores whether a configured set of skills (tool names) was observed in each
invocation, optionally requiring them to appear in the given order.

Partial credit is awarded when only a subset of required skills were called.

Config:
  skills (list[str]): Required. Names of skills/tools that must be observed.
  match_type (str, default "ANY_ORDER"):
    "ANY_ORDER" - all required skills must appear; order and extras ignored.
                  Duplicate requirements are handled via Counter.
    "IN_ORDER"  - required skills must appear as a subsequence in the call
                  list (extras between them are allowed, order matters).
    "EXACT"     - called tool names must match required skills exactly
                  (same names, same order, no extras).

Returns NOT_EVALUATED when ``skills`` is missing, non-list, or empty.

Usage in eval_config.yaml:

    evaluators:
      - name: skills_trajectory
        type: remote
        source: github
        ref: evaluators/skills_trajectory/skills_trajectory.py
        threshold: 0.7
        config:
          skills: ["search", "summarize"]
          match_type: ANY_ORDER
"""

from __future__ import annotations

from collections import Counter
from typing import TypedDict

from agentevals_evaluator_sdk import EvalInput, EvalResult, EvalStatus, evaluator


class _Comparison(TypedDict):
    invocation_id: str
    required_skills: list[str]
    called_tools: list[str]
    score: float


def _skills_score(required: list[str], called: list[str], match_type: str) -> float:
    """Return the fraction of *required* skills satisfied in *called*.

    Args:
        required: Ordered list of required skill/tool names.
        called:   Ordered list of tool names actually called.
        match_type: One of ``"ANY_ORDER"``, ``"IN_ORDER"``, or ``"EXACT"``.

    Returns:
        A float in ``[0.0, 1.0]``.
    """
    if not required:
        return 1.0

    if match_type == "EXACT":
        return 1.0 if called == required else 0.0

    if match_type == "IN_ORDER":
        # Subsequence check: each required skill must appear after the previous hit.
        pos = 0
        hits = 0
        for skill in required:
            while pos < len(called):
                if called[pos] == skill:
                    hits += 1
                    pos += 1
                    break
                pos += 1
        return hits / len(required)

    # ANY_ORDER: duplicate-aware fractional match using Counter.
    called_counts = Counter(called)
    required_counts = Counter(required)
    hits = sum(min(required_counts[s], called_counts[s]) for s in required_counts)
    return hits / len(required)


@evaluator
def skills_trajectory(input: EvalInput) -> EvalResult:
    skills = input.config.get("skills")
    n = len(input.invocations)

    if not n:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[],
            details={"reason": "no invocations to evaluate"},
        )

    if not isinstance(skills, list) or not skills:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": "missing or empty config: skills (need a non-empty list of names)"},
        )

    required = [str(s) for s in skills]
    raw_match_type = str(input.config.get("match_type", "ANY_ORDER")).upper()
    valid_match_types = {"ANY_ORDER", "IN_ORDER", "EXACT"}
    if raw_match_type not in valid_match_types:
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={
                "reason": (
                    f"invalid config: match_type={raw_match_type!r}; "
                    f"must be one of {sorted(valid_match_types)}"
                )
            },
        )

    per_invocation_scores: list[float] = []
    comparisons: list[_Comparison] = []

    for inv in input.invocations:
        called = [call.name for call in inv.intermediate_steps.tool_calls]

        score = _skills_score(required, called, raw_match_type)
        per_invocation_scores.append(score)
        comparisons.append(
            {
                "invocation_id": inv.invocation_id,
                "required_skills": required,
                "called_tools": called,
                "score": score,
            }
        )

    overall = sum(per_invocation_scores) / len(per_invocation_scores) if per_invocation_scores else 0.0
    return EvalResult(
        score=overall,
        per_invocation_scores=per_invocation_scores,
        details={"comparisons": comparisons},
    )


if __name__ == "__main__":
    skills_trajectory.run()
