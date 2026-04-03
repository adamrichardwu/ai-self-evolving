import json
from pathlib import Path

import torch
from torch.nn.utils.rnn import pad_sequence
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_job_spec(job_spec_path: str) -> dict:
    path = Path(job_spec_path).resolve()
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_stage(job_spec: dict, stage_name: str) -> dict:
    for stage in job_spec.get("stages", []):
        if stage.get("name") == stage_name:
            return stage
    raise ValueError(f"Stage not found: {stage_name}")


def load_jsonl(path: str) -> list[dict]:
    rows: list[dict] = []
    for line in Path(path).resolve().read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def validate_sft_rows(rows: list[dict]) -> dict[str, int]:
    valid = 0
    for row in rows:
        if row.get("prompt") and row.get("response"):
            valid += 1
    if valid == 0:
        raise ValueError("No valid SFT rows found")
    return {"row_count": len(rows), "valid_row_count": valid}


def validate_preference_rows(rows: list[dict]) -> dict[str, int]:
    valid = 0
    for row in rows:
        if row.get("prompt") and row.get("chosen_response") and row.get("rejected_response"):
            valid += 1
    if valid == 0:
        raise ValueError("No valid preference rows found")
    return {"row_count": len(rows), "valid_row_count": valid}


def prepare_run_directory(output_dir: str, run_name: str) -> Path:
    path = Path(output_dir).resolve() / run_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_tokenizer_and_model(model_path: str):
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
    )
    model.config.pad_token_id = tokenizer.pad_token_id
    return tokenizer, model


def render_supervised_text(prompt: str, response: str) -> tuple[str, str]:
    prompt_prefix = f"User: {prompt.strip()}\nAssistant:"
    full_text = f"{prompt_prefix} {response.strip()}"
    return prompt_prefix, full_text


def build_sft_features(rows: list[dict], tokenizer, max_length: int) -> list[dict[str, torch.Tensor]]:
    features: list[dict[str, torch.Tensor]] = []
    for row in rows:
        prompt_prefix, full_text = render_supervised_text(row["prompt"], row["response"])
        encoded_full = tokenizer(full_text, truncation=True, max_length=max_length, return_tensors="pt")
        encoded_prompt = tokenizer(prompt_prefix, truncation=True, max_length=max_length, return_tensors="pt")
        input_ids = encoded_full["input_ids"][0]
        attention_mask = encoded_full["attention_mask"][0]
        labels = input_ids.clone()
        prompt_length = min(encoded_prompt["input_ids"].shape[1], labels.shape[0])
        labels[:prompt_length] = -100
        features.append(
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "labels": labels,
            }
        )
    return features


def pad_batch(features: list[dict[str, torch.Tensor]], pad_token_id: int) -> dict[str, torch.Tensor]:
    input_ids = pad_sequence([item["input_ids"] for item in features], batch_first=True, padding_value=pad_token_id)
    attention_mask = pad_sequence([item["attention_mask"] for item in features], batch_first=True, padding_value=0)
    labels = pad_sequence([item["labels"] for item in features], batch_first=True, padding_value=-100)
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


def cycle_batches(features: list[dict[str, torch.Tensor]], batch_size: int):
    if not features:
        raise ValueError("No training features available")
    index = 0
    while True:
        batch = []
        for _ in range(batch_size):
            batch.append(features[index % len(features)])
            index += 1
        yield batch


def move_batch_to_device(batch: dict[str, torch.Tensor], device: torch.device) -> dict[str, torch.Tensor]:
    return {key: value.to(device) for key, value in batch.items()}


def save_model_artifacts(model, tokenizer, output_dir: Path) -> str:
    model_dir = output_dir / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(model_dir)
    tokenizer.save_pretrained(model_dir)
    return str(model_dir)


def write_training_result(run_dir: Path, payload: dict) -> None:
    write_json(run_dir / "run_manifest.json", payload)