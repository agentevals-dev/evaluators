"""Community evaluator: token_efficiency

Scores how efficiently the agent used tokens relative to a budget.
Uses performance_metrics from trace data when available, falls back to
counting tool calls as a rough proxy.

Config options:
  max_tokens (int): Token budget (default: 200000)
  weight_input (float): Weight for input tokens in scoring (default: 0.7)
  weight_output (float): Weight for output tokens in scoring (default: 0.3)
"""

from agentevals_evaluator_sdk import EvalInput, EvalResult, evaluator


def _extract_tokens(inv) -> dict | None:
    """Extract token counts from an invocation's performance_metrics or metadata."""
    # Check performance_metrics (primary source from OTel trace data)
    perf = getattr(inv, "performance_metrics", None)
    if perf is None and hasattr(inv, "__getitem__"):
        try:
            perf = inv["performance_metrics"]
        except (KeyError, TypeError):
            perf = None

    if isinstance(perf, dict):
        input_t = perf.get("input_tokens") or perf.get("prompt_tokens")
        output_t = perf.get("output_tokens") or perf.get("completion_tokens")
        if input_t is not None or output_t is not None:
            return {
                "input_tokens": int(input_t or 0),
                "output_tokens": int(output_t or 0),
            }

    # Check performance_budget on invocation (eval_set integration)
    budget = getattr(inv, "performance_budget", None)
    if budget is None and hasattr(inv, "__getitem__"):
        try:
            budget = inv["performance_budget"]
        except (KeyError, TypeError):
            pass

    # No token data available
    return None


@evaluator
def token_efficiency(input: EvalInput) -> EvalResult:
    max_tokens = input.config.get("max_tokens", 200000)
    weight_input = input.config.get("weight_input", 0.7)
    weight_output = input.config.get("weight_output", 0.3)

    scores: list[float] = []
    details_items: list[str] = []
    has_data = False

    for inv in input.invocations:
        tokens = _extract_tokens(inv)

        if tokens is None:
            # No token data — score based on tool call count as rough proxy
            # More tool calls ≈ more tokens used
            tool_count = len(inv.intermediate_steps.tool_calls) if inv.intermediate_steps else 0
            if tool_count == 0:
                scores.append(0.5)  # No data, neutral score
                details_items.append(f"{inv.invocation_id}: no token data available")
            else:
                # Rough heuristic: assume ~5000 tokens per tool call
                estimated = tool_count * 5000
                score = max(0.0, min(1.0, 1.0 - (estimated / max_tokens)))
                scores.append(score)
                details_items.append(
                    f"{inv.invocation_id}: estimated ~{estimated} tokens from {tool_count} tool calls"
                )
            continue

        has_data = True
        input_t = tokens["input_tokens"]
        output_t = tokens["output_tokens"]
        weighted_total = (input_t * weight_input) + (output_t * weight_output)
        weighted_budget = max_tokens * 1.0  # Budget applies to weighted total

        score = max(0.0, min(1.0, 1.0 - (weighted_total / weighted_budget)))
        scores.append(score)
        details_items.append(
            f"{inv.invocation_id}: {input_t} input + {output_t} output = "
            f"{input_t + output_t} total (weighted: {weighted_total:.0f}/{weighted_budget:.0f})"
        )

    overall = sum(scores) / len(scores) if scores else 0.0

    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={
            "token_details": details_items,
            "has_trace_data": has_data,
            "max_tokens": max_tokens,
        },
    )


if __name__ == "__main__":
    token_efficiency.run()
