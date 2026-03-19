"""Custom evaluator: peters_evaluator

Usage in eval_config.yaml:

    metrics:
      - name: peters_evaluator
        type: code
        path: ./peters_evaluator/peters_evaluator.py
        threshold: 0.5
"""

from agentevals_grader_sdk import grader, EvalInput, EvalResult


@grader
def peters_evaluator(input: EvalInput) -> EvalResult:
    return EvalResult(score=0.123, details={"message": "All good"})


if __name__ == "__main__":
    peters_evaluator.run()
