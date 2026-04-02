from pydantic import BaseModel, Field


class CreateCoreCapabilityDatasetRequest(BaseModel):
    objective: str = "improve core reasoning, identity stability, and goal alignment"
    max_runtime_traces: int = Field(default=8, ge=0, le=32)
    include_runtime_examples: bool = True
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
    target_capabilities: list[str] = Field(default_factory=list)
    policy_source: str = "recommended"


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


class CoreCapabilityExportJobResponse(BaseModel):
    task_id: str
    task_name: str
    status: str