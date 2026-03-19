"""Community evaluator: response_quality

Checks that every invocation has a non-empty response, meets a configurable
minimum length, and doesn't just parrot back the user input.

Config options:
  min_response_length (int): Minimum character length for responses (default: 10)
"""

from agentevals_grader_sdk import grader, EvalInput, EvalResult


@grader
def response_quality(input: EvalInput) -> EvalResult:
    min_len = input.config.get("min_response_length", 10)
    scores: list[float] = []
    issues: list[str] = []

    for inv in input.invocations:
        score = 1.0

        if not inv.final_response:
            score = 0.0
            issues.append(f"{inv.invocation_id}: no response")
            scores.append(score)
            continue

        if len(inv.final_response.strip()) < min_len:
            score -= 0.3
            issues.append(
                f"{inv.invocation_id}: response too short "
                f"({len(inv.final_response.strip())} < {min_len} chars)"
            )

        if (
            inv.user_content
            and inv.final_response.strip().lower() == inv.user_content.strip().lower()
        ):
            score -= 0.5
            issues.append(f"{inv.invocation_id}: response echoes user input")

        scores.append(max(0.0, score))

    overall = sum(scores) / len(scores) if scores else 0.0

    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"issues": issues} if issues else None,
    )


if __name__ == "__main__":
    response_quality.run()
