import argparse
import json
from pathlib import Path

import torch

from train.common import (
    build_sft_features,
    cycle_batches,
    load_job_spec,
    load_jsonl,
    load_tokenizer_and_model,
    move_batch_to_device,
    pad_batch,
    prepare_run_directory,
    resolve_device,
    resolve_stage,
    save_model_artifacts,
    validate_sft_rows,
    write_json,
    write_training_result,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a local SFT run from a core capability training job spec.")
    parser.add_argument("--job-spec", required=True)
    parser.add_argument("--run-name", default="sft-run")
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    job_spec = load_job_spec(args.job_spec)
    stage = resolve_stage(job_spec, "sft")
    rows = load_jsonl(stage["dataset_path"])
    stats = validate_sft_rows(rows)
    run_dir = prepare_run_directory(stage["output_dir"], args.run_name)

    if args.dry_run:
        run_manifest = {
            "status": "dry_run_prepared",
            "stage": "sft",
            "job_spec_path": str(Path(args.job_spec).resolve()),
            "dataset_path": stage["dataset_path"],
            "output_dir": str(run_dir),
            "format": stage["format"],
            "stats": stats,
            "max_steps": args.max_steps,
            "learning_rate": args.learning_rate,
            "batch_size": args.batch_size,
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
    features = build_sft_features(rows, tokenizer, args.max_length)
    batch_iterator = cycle_batches(features, args.batch_size)
    losses: list[float] = []

    for _ in range(args.max_steps):
        batch_features = next(batch_iterator)
        batch = pad_batch(batch_features, tokenizer.pad_token_id)
        batch = move_batch_to_device(batch, device)
        outputs = model(**batch)
        loss = outputs.loss
        loss.backward()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        losses.append(float(loss.detach().cpu().item()))

    model_dir = save_model_artifacts(model, tokenizer, run_dir)
    run_manifest = {
        "status": "trained",
        "stage": "sft",
        "job_spec_path": str(Path(args.job_spec).resolve()),
        "dataset_path": stage["dataset_path"],
        "output_dir": str(run_dir),
        "model_dir": model_dir,
        "format": stage["format"],
        "stats": stats,
        "max_steps": args.max_steps,
        "learning_rate": args.learning_rate,
        "batch_size": args.batch_size,
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