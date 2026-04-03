from pydantic import BaseModel, Field


class CreateCoreCapabilityDatasetRequest(BaseModel):
    objective: str = "improve core reasoning, identity stability, and goal alignment"
    max_runtime_traces: int = Field(default=8, ge=0, le=32)
    max_dialogue_examples: int = Field(default=6, ge=0, le=24)
    include_runtime_examples: bool = True
    include_dialogue_examples: bool = True
    include_benchmark_examples: bool = True


class CreateCoreCapabilityExportRequest(CreateCoreCapabilityDatasetRequest):
    export_label: str = ""


class CoreCapabilitySFTExampleResponse(BaseModel):
    prompt: str
    response: str
    source: str
    target_capability: str
    metadata: dict = Field(default_factory=dict)


class CoreCapabilityPreferenceExampleResponse(BaseModel):
    prompt: str
    chosen_response: str
    rejected_response: str
    source: str
    target_capability: str
    metadata: dict = Field(default_factory=dict)


class CoreCapabilityDatasetSummaryResponse(BaseModel):
    sft_example_count: int = 0
    preference_example_count: int = 0
    dialogue_example_count: int = 0
    runtime_example_count: int = 0
    benchmark_example_count: int = 0
    target_capabilities: list[str] = Field(default_factory=list)
    policy_source: str = "recommended"


class CoreCapabilityDatasetFileResponse(BaseModel):
    path: str
    format: str
    field_map: dict = Field(default_factory=dict)
    example_count: int = 0


class CoreCapabilityTrainingManifestResponse(BaseModel):
    schema_version: str
    base_model: str
    stages: list[dict] = Field(default_factory=list)
    evaluation_plan: dict = Field(default_factory=dict)
    datasets: dict[str, CoreCapabilityDatasetFileResponse] = Field(default_factory=dict)


class CoreCapabilityDatasetResponse(BaseModel):
    agent_id: str
    chosen_name: str
    objective: str
    active_policy: dict = Field(default_factory=dict)
    policy_source: str = "recommended"
    sft_examples: list[CoreCapabilitySFTExampleResponse] = Field(default_factory=list)
    preference_examples: list[CoreCapabilityPreferenceExampleResponse] = Field(default_factory=list)
    summary: CoreCapabilityDatasetSummaryResponse


class CoreCapabilityExportResponse(BaseModel):
    export_id: str
    agent_id: str
    chosen_name: str
    objective: str
    status: str
    policy_source: str = "recommended"
    bundle_dir: str
    manifest_path: str
    sft_dataset_path: str
    preference_dataset_path: str
    sft_example_count: int = 0
    preference_example_count: int = 0
    training_manifest: CoreCapabilityTrainingManifestResponse


class CreateCoreCapabilityEvaluationRequest(BaseModel):
    manifest_path: str


class CreateCoreCapabilityTrainingJobRequest(BaseModel):
    manifest_path: str
    job_label: str = ""
    mode: str = "sft_then_preference"


class CreateCoreCapabilityTrainingEvaluationRequest(BaseModel):
    run_manifest_path: str
    max_examples: int = Field(default=8, ge=1, le=32)
    dry_run: bool = False


class CoreCapabilityEvaluationResponse(BaseModel):
    status: str
    verdict: str
    manifest_path: str
    sft_example_count: int = 0
    preference_example_count: int = 0
    dialogue_example_count: int = 0
    capability_coverage: int = 0
    average_prompt_length: float = 0.0
    average_response_length: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class CoreCapabilityEvaluationJobResponse(BaseModel):
    task_id: str
    task_name: str
    status: str


class CoreCapabilityTrainingJobResponse(BaseModel):
    status: str
    manifest_path: str
    job_spec_path: str
    base_model: str
    mode: str
    stages: list[dict] = Field(default_factory=list)


class CoreCapabilityTrainingJobQueueResponse(BaseModel):
    task_id: str
    task_name: str
    status: str


class CoreCapabilityTrainingEvaluationResponse(BaseModel):
    status: str
    run_manifest_path: str
    evaluation_path: str
    baseline_model_path: str
    candidate_model_path: str
    sft_loss_baseline: float = 0.0
    sft_loss_candidate: float = 0.0
    preference_margin_baseline: float = 0.0
    preference_margin_candidate: float = 0.0
    overall_delta: float = 0.0
    verdict: str = "needs_review"


class CoreCapabilityTrainingEvaluationQueueResponse(BaseModel):
    task_id: str
    task_name: str
    status: str


class CoreCapabilityExportJobResponse(BaseModel):
    task_id: str
    task_name: str
    status: str