"""Community evaluator: tool_efficiency

Scores tool usage effectiveness per invocation.  Penalizes duplicate calls
(same tool name + args), error responses, and budget overruns.

Score per invocation:
  useful_calls = total - duplicates - errors
  efficiency   = useful_calls / total
  budget_factor = clamp(1.0 - max(0, total - max_tool_calls) / max_tool_calls, 0, 1)
  min_factor    = total / min_tool_calls  (when total < min_tool_calls, else 1.0)
  score = clamp(efficiency * budget_factor * min_factor, 0, 1)

If total == 0:  score = 0.0 when min_tool_calls > 0, else 1.0.

Config options:
  max_tool_calls      (int):  Budget; calls beyond this are penalized (default: 15)
  min_tool_calls      (int):  Minimum required; 0 means optional      (default: 0)
  penalize_duplicates (bool): Count duplicate calls as waste           (default: true)
  penalize_errors     (bool): Count error responses as waste           (default: true)
"""

from __future__ import annotations

import json

from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator


def _call_signature(call) -> str:
    """Deterministic signature for deduplication: 'tool_name::sorted_args_json'."""
    try:
        args_str = json.dumps(call.args, sort_keys=True, default=str)
    except (TypeError, ValueError):
        args_str = str(call.args)
    return f"{call.name}::{args_str}"


def _is_error_response(response) -> bool:
    """Check if a tool response indicates an error via its status field."""
    status = (response.status or "").lower()
    return status in ("error", "failed", "failure")


@evaluator
def tool_efficiency(input: EvalInput) -> EvalResult:
    max_tool_calls = input.config.get("max_tool_calls", 15)
    min_tool_calls = input.config.get("min_tool_calls", 0)
    penalize_duplicates = input.config.get("penalize_duplicates", True)
    penalize_errors = input.config.get("penalize_errors", True)

    scores: list[float] = []
    inv_details: list[dict] = []

    for inv in input.invocations:
        tool_calls = inv.intermediate_steps.tool_calls
        tool_responses = inv.intermediate_steps.tool_responses
        total = len(tool_calls)

        if total == 0:
            if min_tool_calls > 0:
                scores.append(0.0)
                inv_details.append({
                    "invocation_id": inv.invocation_id,
                    "score": 0.0,
                    "reason": f"no tool calls (min required: {min_tool_calls})",
                })
            else:
                scores.append(1.0)
                inv_details.append({
                    "invocation_id": inv.invocation_id,
                    "score": 1.0,
                    "reason": "no tool calls (tools optional)",
                })
            continue

        dupes = 0
        if penalize_duplicates:
            seen: dict[str, int] = {}
            for call in tool_calls:
                sig = _call_signature(call)
                seen[sig] = seen.get(sig, 0) + 1
            dupes = sum(count - 1 for count in seen.values() if count > 1)

        errors = 0
        if penalize_errors:
            errors = sum(1 for r in tool_responses if _is_error_response(r))

        useful = max(0, total - dupes - errors)
        efficiency = useful / total

        budget_factor = 1.0
        if max_tool_calls > 0 and total > max_tool_calls:
            budget_factor = max(0.0, 1.0 - (total - max_tool_calls) / max_tool_calls)

        min_factor = 1.0
        if min_tool_calls > 0 and total < min_tool_calls:
            min_factor = total / min_tool_calls

        score = max(0.0, min(1.0, efficiency * budget_factor * min_factor))
        scores.append(score)

        detail: dict = {
            "invocation_id": inv.invocation_id,
            "score": round(score, 4),
            "total_calls": total,
            "useful_calls": useful,
        }
        if dupes:
            detail["duplicate_calls"] = dupes
        if errors:
            detail["error_responses"] = errors
        if budget_factor < 1.0:
            detail["budget_factor"] = round(budget_factor, 4)
        if min_factor < 1.0:
            detail["min_factor"] = round(min_factor, 4)
            detail["min_tool_calls"] = min_tool_calls
        inv_details.append(detail)

    overall = sum(scores) / len(scores) if scores else 0.0

    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"per_invocation": inv_details},
    )


if __name__ == "__main__":
    tool_efficiency.run()
