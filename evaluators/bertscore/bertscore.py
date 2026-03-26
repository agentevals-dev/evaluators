"""BERTScore semantic similarity evaluator.

Computes BERTScore (precision, recall, F1) between each invocation's response
and a reference text using contextual embeddings and cosine similarity.

Config:
  expected (str): Required. Reference text to compare against. If omitted, returns NOT_EVALUATED.
  model_name (str, default "distilbert-base-uncased"): HuggingFace model for embeddings.
  metric (str, default "f1"): Primary score component: "precision", "recall", or "f1".

Usage:
    config:
      expected: "reference answer"
      metric: "f1"
"""

from __future__ import annotations

import sys

import torch
from transformers import AutoModel, AutoTokenizer

from agentevals_evaluator_sdk import EvalInput, EvalResult, EvalStatus, evaluator

_VALID_METRICS = ("precision", "recall", "f1")


def _compute_bertscore(
    candidate: str,
    reference: str,
    tokenizer: AutoTokenizer,
    model: AutoModel,
    device: torch.device,
) -> dict[str, float]:
    """Compute BERTScore precision, recall, and F1 for a candidate-reference pair."""
    cand = tokenizer(candidate, return_tensors="pt", padding=True, truncation=True).to(device)
    ref = tokenizer(reference, return_tensors="pt", padding=True, truncation=True).to(device)

    with torch.no_grad():
        cand_emb = torch.nn.functional.normalize(model(**cand).last_hidden_state, dim=-1)
        ref_emb = torch.nn.functional.normalize(model(**ref).last_hidden_state, dim=-1)

    sim = torch.bmm(cand_emb, ref_emb.transpose(1, 2))

    precision = sim.max(dim=2)[0].mean().item()
    recall = sim.max(dim=1)[0].mean().item()
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}


@evaluator
def bertscore(input: EvalInput) -> EvalResult:
    expected = input.config.get("expected")
    if expected is None:
        n = len(input.invocations)
        return EvalResult(
            score=0.0,
            status=EvalStatus.NOT_EVALUATED,
            per_invocation_scores=[None] * n,
            details={"reason": "missing config: expected"},
        )

    metric = input.config.get("metric", "f1")
    if metric not in _VALID_METRICS:
        print(f"WARNING: invalid metric '{metric}', using 'f1'", file=sys.stderr)
        metric = "f1"

    model_name = input.config.get("model_name", "distilbert-base-uncased")
    reference = str(expected)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device)
    model.eval()

    scores: list[float] = []
    details_rows: list[dict] = []

    for inv in input.invocations:
        result = _compute_bertscore(inv.final_response or "", reference, tokenizer, model, device)
        scores.append(result[metric])
        details_rows.append({"invocation_id": inv.invocation_id, **result})

    overall = sum(scores) / len(scores) if scores else 0.0
    return EvalResult(
        score=overall,
        per_invocation_scores=scores,
        details={"metric": metric, "model_name": model_name, "per_invocation": details_rows},
    )


if __name__ == "__main__":
    bertscore.run()
