"""Community evaluator: tool_efficiency

Scores tool usage effectiveness. Penalizes duplicate calls (same tool + args),
error responses, and budget overruns.

Config: max_tool_calls (int, default 15), penalize_duplicates (bool, default true),
        penalize_errors (bool, default true)
"""

import json
from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator


def _call_signature(call) -> str:
    name = call.get("name", "") if isinstance(call, dict) else getattr(call, "name", "")
    args = call.get("args", {}) if isinstance(call, dict) else getattr(call, "args", {})
    try:
        args_str = json.dumps(args, sort_keys=True, default=str)
    except (TypeError, ValueError):
        args_str = str(args)
    return f"{name}::{args_str}"


def _is_error_response(response) -> bool:
    """Check if a tool response indicates an error via its status field."""
    status = response.get("status", "") if isinstance(response, dict) else getattr(response, "status", "")
    return str(status).lower() in ("error", "failed", "failure")


@evaluator
def tool_efficiency(input: EvalInput) -> EvalResult:
    max_tool_calls = input.config.get("max_tool_calls", 15)
    penalize_duplicates = input.config.get("penalize_duplicates", True)
    penalize_errors = input.config.get("penalize_errors", True)

    scores: list[float] = []
    details_items: list[str] = []

    for inv in input.invocations:
        tool_calls = inv.intermediate_steps.tool_calls if inv.intermediate_steps else []
        tool_responses = inv.intermediate_steps.tool_responses if inv.intermediate_steps else []
        total = len(tool_calls)

        if total == 0:
            scores.append(1.0)
            details_items.append(f"{inv.invocation_id}: no tool calls")
            continue

        seen: dict[str, int] = {}
        for call in tool_calls:
            sig = _call_signature(call)
            seen[sig] = seen.get(sig, 0) + 1

        dupes = sum(c - 1 for c in seen.values() if c > 1) if penalize_duplicates else 0
        errors = sum(1 for r in tool_responses if _is_error_response(r)) if penalize_errors else 0
        useful = max(0, total - dupes - errors)

        efficiency = useful / total
        budget_factor = max(0.0, 1.0 - max(0, total - max_tool_calls) / max_tool_calls)
        score = max(0.0, min(1.0, efficiency * budget_factor))
        scores.append(score)

        parts = [f"total={total}", f"useful={useful}"]
        if dupes: parts.append(f"dupes={dupes}")
        if errors: parts.append(f"errors={errors}")
        details_items.append(f"{inv.invocation_id}: {', '.join(parts)}")

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(score=overall, per_invocation_scores=scores, details={"tool_details": details_items})


if __name__ == "__main__":
    tool_efficiency.run()
