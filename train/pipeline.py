import argparse
import json
import subprocess
import sys
from pathlib import Path

from train.common import load_job_spec, resolve_stage, write_json


def _extract_payload(stdout: str) -> dict:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise ValueError("Training command did not emit a JSON payload")


def _run_stage(command: list[str], cwd: Path) -> dict:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return _extract_payload(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local core capability training pipeline sequentially.")
    parser.add_argument("--job-spec", required=True)
    parser.add_argument("--run-label", default="pipeline")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    job_spec_path = Path(args.job_spec).resolve()
    job_spec = load_job_spec(str(job_spec_path))
    repo_root = Path(__file__).resolve().parents[1]
    pipeline_manifest_path = job_spec_path.parent / f"pipeline_run_{args.run_label}.json"

    sft_stage = resolve_stage(job_spec, "sft")
    sft_config = sft_stage.get("training_config", {})
    sft_command = [
        sys.executable,
        "-m",
        "train.sft",
        "--job-spec",
        str(job_spec_path),
        "--run-name",
        f"{args.run_label}-sft",
        "--base-model",
        str(job_spec["base_model"]),
        "--max-steps",
        str(sft_config.get("max_steps", 12)),
        "--learning-rate",
        str(sft_config.get("learning_rate", 5e-5)),
        "--batch-size",
        str(sft_config.get("batch_size", 1)),
        "--max-length",
        str(sft_config.get("max_length", 256)),
    ]
    if args.dry_run:
        sft_command.append("--dry-run")
    sft_result = _run_stage(sft_command, repo_root)

    stage_results = [sft_result]
    final_result = sft_result

    if job_spec.get("mode") == "sft_then_preference":
        preference_stage = resolve_stage(job_spec, "preference_optimization")
        preference_config = preference_stage.get("training_config", {})
        preference_base_model = sft_result.get("model_dir") or sft_result.get("base_model_path") or str(job_spec["base_model"])
        preference_command = [
            sys.executable,
            "-m",
            "train.preference",
            "--job-spec",
            str(job_spec_path),
            "--run-name",
            f"{args.run_label}-preference",
            "--base-model",
            str(preference_base_model),
            "--max-steps",
            str(preference_config.get("max_steps", 8)),
            "--learning-rate",
            str(preference_config.get("learning_rate", 1e-5)),
            "--beta",
            str(preference_config.get("beta", 0.1)),
            "--max-length",
            str(preference_config.get("max_length", 256)),
        ]
        if args.dry_run:
            preference_command.append("--dry-run")
        preference_result = _run_stage(preference_command, repo_root)
        stage_results.append(preference_result)
        final_result = preference_result

    payload = {
        "status": "dry_run_prepared" if args.dry_run else "completed",
        "job_spec_path": str(job_spec_path),
        "pipeline_manifest_path": str(pipeline_manifest_path),
        "mode": job_spec.get("mode", "sft_only"),
        "run_label": args.run_label,
        "final_run_manifest_path": str(Path(final_result["output_dir"]).resolve() / "run_manifest.json"),
        "final_model_dir": final_result.get("model_dir", ""),
        "stage_results": stage_results,
    }
    write_json(pipeline_manifest_path, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())