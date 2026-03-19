"""Custom grader: peters_grader

Usage in eval_config.yaml:

    metrics:
      - name: peters_grader
        type: code
        path: ./peters_grader/peters_grader.py
        threshold: 0.5
"""

from agentevals_grader_sdk import grader, EvalInput, EvalResult


@grader
def peters_grader(input: EvalInput) -> EvalResult:
    return EvalResult(score=0.123, details={"message": "All good"})
