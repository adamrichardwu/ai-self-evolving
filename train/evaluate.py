import argparse
import json
from pathlib import Path

import torch

from train.common import (
    build_sft_features,
    load_job_spec,
    load_jsonl,
    load_tokenizer_and_model,
    move_batch_to_device,
    pad_batch,
    resolve_device,
    validate_preference_rows,
    validate_sft_rows,
    write_json,
)


def _build_preference_example(tokenizer, prompt: str, response: str, max_length: int) -> dict[str, torch.Tensor]:
    prompt_prefix = f"User: {prompt.strip()}\nAssistant:"
    full_text = f"{prompt_prefix} {response.strip()}"
    encoded_full = tokenizer(full_text, truncation=True, max_length=max_length, return_tensors="pt")
    encoded_prompt = tokenizer(prompt_prefix, truncation=True, max_length=max_length, return_tensors="pt")
    input_ids = encoded_full["input_ids"][0]
    attention_mask = encoded_full["attention_mask"][0]
    labels = input_ids.clone()
    prompt_length = min(encoded_prompt["input_ids"].shape[1], labels.shape[0])
    labels[:prompt_length] = -100
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


def _sequence_log_probability(model, batch: dict[str, torch.Tensor]) -> torch.Tensor:
    outputs = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"])
    logits = outputs.logits[:, :-1, :]
    labels = batch["labels"][:, 1:]
    log_probs = torch.log_softmax(logits, dim=-1)
    safe_labels = labels.clamp_min(0)
    token_log_probs = log_probs.gather(dim=-1, index=safe_labels.unsqueeze(-1)).squeeze(-1)
    mask = (labels != -100).float()
    return (token_log_probs * mask).sum(dim=-1)


def _average_sft_loss(model, tokenizer, rows: list[dict], max_length: int, max_examples: int, device: torch.device) -> float:
    features = build_sft_features(rows[:max_examples], tokenizer, max_length)
    losses: list[float] = []
    with torch.no_grad():
        for feature in features:
            batch = pad_batch([feature], tokenizer.pad_token_id)
            batch = move_batch_to_device(batch, device)
            outputs = model(**batch)
            losses.append(float(outputs.loss.detach().cpu().item()))
    return sum(losses) / max(1, len(losses))


def _average_preference_margin(model, tokenizer, rows: list[dict], max_length: int, max_examples: int, device: torch.device) -> float:
    margins: list[float] = []
    with torch.no_grad():
        for row in rows[:max_examples]:
            chosen = _build_preference_example(tokenizer, row["prompt"], row["chosen_response"], max_length)
            rejected = _build_preference_example(tokenizer, row["prompt"], row["rejected_response"], max_length)
            chosen_batch = move_batch_to_device({key: value.unsqueeze(0) for key, value in chosen.items()}, device)
            rejected_batch = move_batch_to_device({key: value.unsqueeze(0) for key, value in rejected.items()}, device)
            chosen_log_prob = _sequence_log_probability(model, chosen_batch)
            rejected_log_prob = _sequence_log_probability(model, rejected_batch)
            margins.append(float((chosen_log_prob - rejected_log_prob).detach().cpu().item()))
    return sum(margins) / max(1, len(margins))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a trained local run against the baseline model.")
    parser.add_argument("--run-manifest", required=True)
    parser.add_argument("--max-examples", type=int, default=8)
    args = parser.parse_args()

    run_manifest_path = Path(args.run_manifest).resolve()
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    job_spec = load_job_spec(run_manifest["job_spec_path"])
    base_model_path = job_spec["base_model"]
    candidate_model_path = run_manifest["model_dir"]
    sft_dataset_path = job_spec["stages"][0]["dataset_path"]
    preference_stage = next((stage for stage in job_spec.get("stages", []) if stage.get("name") == "preference_optimization"), None)
    preference_dataset_path = preference_stage["dataset_path"] if preference_stage is not None else ""

    sft_rows = load_jsonl(sft_dataset_path)
    validate_sft_rows(sft_rows)
    preference_rows = load_jsonl(preference_dataset_path) if preference_dataset_path else []
    if preference_rows:
        validate_preference_rows(preference_rows)

    device = resolve_device()
    base_tokenizer, base_model = load_tokenizer_and_model(base_model_path)
    candidate_tokenizer, candidate_model = load_tokenizer_and_model(candidate_model_path)
    base_model.to(device)
    candidate_model.to(device)
    base_model.eval()
    candidate_model.eval()

    max_length = int(run_manifest.get("max_length", 256))
    sft_loss_baseline = _average_sft_loss(base_model, base_tokenizer, sft_rows, max_length, args.max_examples, device)
    sft_loss_candidate = _average_sft_loss(candidate_model, candidate_tokenizer, sft_rows, max_length, args.max_examples, device)
    preference_margin_baseline = 0.0
    preference_margin_candidate = 0.0
    if preference_rows:
        preference_margin_baseline = _average_preference_margin(base_model, base_tokenizer, preference_rows, max_length, args.max_examples, device)
        preference_margin_candidate = _average_preference_margin(candidate_model, candidate_tokenizer, preference_rows, max_length, args.max_examples, device)

    sft_improvement = sft_loss_baseline - sft_loss_candidate
    preference_improvement = preference_margin_candidate - preference_margin_baseline
    overall_delta = sft_improvement + preference_improvement
    verdict = "promote_candidate" if overall_delta > 0 else "needs_review"

    payload = {
        "status": "completed",
        "run_manifest_path": str(run_manifest_path),
        "evaluation_path": str(run_manifest_path.parent / "training_evaluation.json"),
        "baseline_model_path": base_model_path,
        "candidate_model_path": candidate_model_path,
        "sft_loss_baseline": sft_loss_baseline,
        "sft_loss_candidate": sft_loss_candidate,
        "preference_margin_baseline": preference_margin_baseline,
        "preference_margin_candidate": preference_margin_candidate,
        "overall_delta": overall_delta,
        "verdict": verdict,
    }
    write_json(run_manifest_path.parent / "training_evaluation.json", payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())