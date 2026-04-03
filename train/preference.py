import argparse
import json
import math
from pathlib import Path

import torch

from train.common import (
    load_tokenizer_and_model,
    load_job_spec,
    load_jsonl,
    move_batch_to_device,
    resolve_device,
    prepare_run_directory,
    resolve_stage,
    save_model_artifacts,
    validate_preference_rows,
    write_json,
    write_training_result,
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local preference optimization run from a core capability training job spec.")
    parser.add_argument("--job-spec", required=True)
    parser.add_argument("--run-name", default="preference-run")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--beta", type=float, default=0.1)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    job_spec = load_job_spec(args.job_spec)
    stage = resolve_stage(job_spec, "preference_optimization")
    rows = load_jsonl(stage["dataset_path"])
    stats = validate_preference_rows(rows)
    run_dir = prepare_run_directory(stage["output_dir"], args.run_name)

    if args.dry_run:
        run_manifest = {
            "status": "dry_run_prepared",
            "stage": "preference_optimization",
            "job_spec_path": str(Path(args.job_spec).resolve()),
            "dataset_path": stage["dataset_path"],
            "output_dir": str(run_dir),
            "format": stage["format"],
            "stats": stats,
            "max_steps": args.max_steps,
            "learning_rate": args.learning_rate,
            "beta": args.beta,
            "max_length": args.max_length,
        }
        write_training_result(run_dir, run_manifest)
        write_json(
            run_dir / "dataset_preview.json",
            {"samples": rows[:3], "sample_count": min(3, len(rows))},
        )
        print(json.dumps(run_manifest, ensure_ascii=False))
        return 0

    tokenizer, model = load_tokenizer_and_model(job_spec["base_model"])
    device = resolve_device()
    model.to(device)
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    losses: list[float] = []

    for step in range(args.max_steps):
        row = rows[step % len(rows)]
        chosen = _build_preference_example(tokenizer, row["prompt"], row["chosen_response"], args.max_length)
        rejected = _build_preference_example(tokenizer, row["prompt"], row["rejected_response"], args.max_length)
        chosen_batch = move_batch_to_device({key: value.unsqueeze(0) for key, value in chosen.items()}, device)
        rejected_batch = move_batch_to_device({key: value.unsqueeze(0) for key, value in rejected.items()}, device)

        chosen_log_prob = _sequence_log_probability(model, chosen_batch)
        rejected_log_prob = _sequence_log_probability(model, rejected_batch)
        loss = -torch.nn.functional.logsigmoid(args.beta * (chosen_log_prob - rejected_log_prob)).mean()
        if not math.isfinite(float(loss.detach().cpu().item())):
            raise ValueError("Preference training loss became non-finite")
        loss.backward()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        losses.append(float(loss.detach().cpu().item()))

    model_dir = save_model_artifacts(model, tokenizer, run_dir)
    run_manifest = {
        "status": "trained",
        "stage": "preference_optimization",
        "job_spec_path": str(Path(args.job_spec).resolve()),
        "dataset_path": stage["dataset_path"],
        "output_dir": str(run_dir),
        "model_dir": model_dir,
        "format": stage["format"],
        "stats": stats,
        "max_steps": args.max_steps,
        "learning_rate": args.learning_rate,
        "beta": args.beta,
        "max_length": args.max_length,
        "loss_history": losses,
    }
    write_training_result(run_dir, run_manifest)
    write_json(
        run_dir / "dataset_preview.json",
        {"samples": rows[:3], "sample_count": min(3, len(rows))},
    )
    print(json.dumps(run_manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())