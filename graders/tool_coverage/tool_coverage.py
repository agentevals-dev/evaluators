"""Community grader: tool_coverage

Verifies that each invocation made at least a minimum number of tool calls.
Useful for ensuring agents actually use their tools rather than hallucinating
answers.

Config options:
  min_tool_calls (int): Minimum tool calls per invocation (default: 1)
"""

from agentevals_grader_sdk import grader, EvalInput, EvalResult


@grader
def tool_coverage(input: EvalInput) -> EvalResult:
    min_calls = input.config.get("min_tool_calls", 1)
    scores: list[float] = []
    details: list[str] = []

    for inv in input.invocations:
        actual = len(inv.tool_calls)
        if actual >= min_calls:
            scores.append(1.0)
        else:
            scores.append(0.0)
            details.append(
                f"{inv.invocation_id}: expected >= {min_calls} tool calls, got {actual}"
            )

    overall = sum(scores) / len(scores) if scores else 0.0

    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"missing_tools": details} if details else None,
    )
