"""Custom evaluator: random_evaluator

This evaluator is a random evaluator that returns a random score between 0 and 1.

Usage in eval_config.yaml:

    evaluators:
      - name: random_evaluator
        type: remote
        source: github
        ref: evaluators/random_evaluator/random_evaluator.py
        threshold: 0.5
        executor: local
"""

from agentevals_evaluator_sdk import evaluator, EvalInput, EvalResult
import random


@evaluator
def random_evaluator(input: EvalInput) -> EvalResult:
    random_score = random.random()
    return EvalResult(score=random_score, details={"message": "All good"})


if __name__ == "__main__":
    random_evaluator.run()
