"""Community evaluator: tool_efficiency

Scores whether the agent used tools effectively. Penalizes duplicate calls
(same tool + same args), error calls, and budget overruns.

Config options:
  max_tool_calls (int): Tool call budget (default: 15)
  penalize_duplicates (bool): Penalize repeated identical calls (default: true)
  penalize_errors (bool): Penalize failed tool calls (default: true)
"""

import json
from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator


def _call_signature(call) -> str:
    """Create a hashable signature for a tool call (name + sorted args)."""
    name = call.get("name", "") if isinstance(call, dict) else getattr(call, "name", "")
    args = call.get("args", {}) if isinstance(call, dict) else getattr(call, "args", {})
    try:
        args_str = json.dumps(args, sort_keys=True, default=str)
    except (TypeError, ValueError):
        args_str = str(args)
    return f"{name}::{args_str}"


def _is_error_response(response) -> bool:
    """Check if a tool response indicates an error."""
    output = response.get("output", "") if isinstance(response, dict) else getattr(response, "output", "")
    output_str = str(output).lower()
    # Check common error indicators
    if any(marker in output_str for marker in ["error", "failed", "exception", "traceback"]):
        return True
    status = response.get("status", "") if isinstance(response, dict) else getattr(response, "status", "")
    if str(status).lower() in ("error", "failed"):
        return True
    return False


@evaluator
def tool_efficiency(input: EvalInput) -> EvalResult:
    max_tool_calls = input.config.get("max_tool_calls", 15)
    penalize_duplicates = input.config.get("penalize_duplicates", True)
    penalize_errors = input.config.get("penalize_errors", True)

    scores: list[float] = []
    details_items: list[str] = []

    for inv in input.invocations:
        tool_calls = inv.intermediate_steps.tool_calls if inv.intermediate_steps else []
        tool_responses = (
            inv.intermediate_steps.tool_responses if inv.intermediate_steps else []
        )
        total = len(tool_calls)

        if total == 0:
            scores.append(1.0)  # No tools needed = perfectly efficient
            details_items.append(f"{inv.invocation_id}: no tool calls (score: 1.0)")
            continue

        # Count duplicates
        seen_signatures: dict[str, int] = {}
        duplicate_count = 0
        for call in tool_calls:
            sig = _call_signature(call)
            seen_signatures[sig] = seen_signatures.get(sig, 0) + 1

        if penalize_duplicates:
            duplicate_count = sum(count - 1 for count in seen_signatures.values() if count > 1)

        # Count errors
        error_count = 0
        if penalize_errors and tool_responses:
            for resp in tool_responses:
                if _is_error_response(resp):
                    error_count += 1

        # Calculate useful calls
        wasted = duplicate_count + error_count
        useful = max(0, total - wasted)

        # Efficiency ratio: useful / total
        efficiency_ratio = useful / total if total > 0 else 1.0

        # Budget penalty: how much over budget
        budget_overrun = max(0, total - max_tool_calls) / max_tool_calls
        budget_factor = max(0.0, 1.0 - budget_overrun)

        score = max(0.0, min(1.0, efficiency_ratio * budget_factor))
        scores.append(score)

        parts = [f"total={total}", f"useful={useful}"]
        if duplicate_count > 0:
            parts.append(f"duplicates={duplicate_count}")
        if error_count > 0:
            parts.append(f"errors={error_count}")
        if total > max_tool_calls:
            parts.append(f"over_budget={total - max_tool_calls}")
        details_items.append(f"{inv.invocation_id}: {', '.join(parts)} (score: {score:.2f})")

    overall = sum(scores) / len(scores) if scores else 0.0

    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={
            "tool_details": details_items,
            "max_tool_calls": max_tool_calls,
        },
    )


if __name__ == "__main__":
    tool_efficiency.run()
