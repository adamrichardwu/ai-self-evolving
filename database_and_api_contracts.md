# 自我进化模型数据库设计与 API 契约

## 1. 目标

本文件定义 MVP 到成长阶段所需的核心数据库表设计，以及最小可用 API 契约。目标是保证：

- 任务执行数据可追踪
- 候选变体可审计
- 评估结果可比较
- 发布与回滚可追溯
- 模块之间通过稳定契约协作

## 2. 数据库选型

推荐主库：PostgreSQL

原因：

- 事务能力强
- JSONB 适合半结构化实验元数据
- 易于做索引、审计与报表
- 与 Python/TypeScript 生态集成成熟

补充存储：

- Redis：短期任务状态、队列缓存、限流
- Qdrant：向量记忆
- Neo4j：结构记忆与依赖图
- MinIO：大对象制品、报告、原始轨迹归档

## 3. PostgreSQL 核心表

### 3.1 task_runs

用途：记录每一次真实任务或评估任务执行。

关键字段：

- id: uuid pk
- task_type: varchar(64)
- request_source: varchar(64)
- input_ref: varchar(255)
- output_ref: varchar(255)
- orchestrator_version: varchar(64)
- strategy_version_id: uuid
- model_version_id: uuid
- status: varchar(32)
- latency_ms: integer
- token_input: integer
- token_output: integer
- cost_value: numeric(12,4)
- user_feedback_score: numeric(4,2)
- safety_flag: boolean
- started_at: timestamptz
- finished_at: timestamptz
- created_at: timestamptz

索引建议：

- idx_task_runs_task_type
- idx_task_runs_strategy_version_id
- idx_task_runs_model_version_id
- idx_task_runs_started_at

### 3.2 task_traces

用途：存储任务轨迹摘要和外部对象引用。

关键字段：

- id: uuid pk
- task_run_id: uuid fk -> task_runs.id
- trace_ref: varchar(255)
- tool_calls_count: integer
- error_count: integer
- summary_json: jsonb
- created_at: timestamptz

### 3.3 failure_clusters

用途：存储失败样本聚类结果。

关键字段：

- id: uuid pk
- cluster_name: varchar(128)
- cluster_signature: varchar(255)
- sample_count: integer
- severity: varchar(32)
- diagnosis_json: jsonb
- created_at: timestamptz
- updated_at: timestamptz

### 3.4 strategy_versions

用途：记录 prompt、workflow、routing 等策略版本。

关键字段：

- id: uuid pk
- name: varchar(128)
- version: varchar(64)
- parent_id: uuid null
- strategy_type: varchar(64)
- config_ref: varchar(255)
- changelog: text
- status: varchar(32)
- created_by: varchar(64)
- created_at: timestamptz

### 3.5 model_versions

用途：记录主模型、小模型、LoRA、reranker 等版本。

关键字段：

- id: uuid pk
- name: varchar(128)
- version: varchar(64)
- model_role: varchar(64)
- base_model: varchar(128)
- artifact_ref: varchar(255)
- registry_ref: varchar(255)
- status: varchar(32)
- created_at: timestamptz

### 3.6 hypotheses

用途：记录每一条改进假设。

关键字段：

- id: uuid pk
- source_type: varchar(64)
- source_ref: varchar(255)
- title: varchar(255)
- description: text
- confidence_score: numeric(5,4)
- risk_level: varchar(32)
- status: varchar(32)
- created_at: timestamptz

### 3.7 variants

用途：记录从假设生成的候选变体。

关键字段：

- id: uuid pk
- hypothesis_id: uuid fk -> hypotheses.id
- parent_strategy_version_id: uuid null
- parent_model_version_id: uuid null
- mutation_type: varchar(64)
- manifest_json: jsonb
- expected_gain: numeric(8,4)
- budget_limit: numeric(12,4)
- risk_level: varchar(32)
- rollback_condition: text
- status: varchar(32)
- created_at: timestamptz

索引建议：

- idx_variants_hypothesis_id
- idx_variants_status
- idx_variants_mutation_type

### 3.8 experiments

用途：记录每一次实验执行实例。

关键字段：

- id: uuid pk
- variant_id: uuid fk -> variants.id
- experiment_type: varchar(64)
- runner_type: varchar(64)
- mlflow_run_id: varchar(128)
- dataset_version: varchar(128)
- status: varchar(32)
- resource_usage_json: jsonb
- started_at: timestamptz
- finished_at: timestamptz
- created_at: timestamptz

### 3.9 evaluation_reports

用途：记录实验评估结果。

关键字段：

- id: uuid pk
- experiment_id: uuid fk -> experiments.id
- benchmark_score: numeric(8,4)
- regression_score: numeric(8,4)
- adversarial_score: numeric(8,4)
- shadow_score: numeric(8,4)
- safety_passed: boolean
- latency_delta: numeric(8,4)
- cost_delta: numeric(8,4)
- utility_score: numeric(8,4)
- verdict: varchar(32)
- report_ref: varchar(255)
- created_at: timestamptz

### 3.10 approvals

用途：记录审批动作。

关键字段：

- id: uuid pk
- target_type: varchar(32)
- target_id: uuid
- decision: varchar(32)
- reviewer: varchar(128)
- reason: text
- policy_snapshot_ref: varchar(255)
- created_at: timestamptz

### 3.11 releases

用途：记录发布、灰度、回滚信息。

关键字段：

- id: uuid pk
- release_type: varchar(32)
- strategy_version_id: uuid null
- model_version_id: uuid null
- evaluation_report_id: uuid
- approval_id: uuid
- environment: varchar(32)
- rollout_percentage: numeric(5,2)
- status: varchar(32)
- rollback_to_release_id: uuid null
- created_at: timestamptz

### 3.12 self_models

用途：记录智能体当前生效的 Self Model 状态。

关键字段：

- id: uuid pk
- agent_id: varchar(128) unique
- chosen_name: varchar(128)
- status: varchar(32)
- current_version: integer
- identity_json: jsonb
- capability_json: jsonb
- goals_json: jsonb
- values_json: jsonb
- affect_json: jsonb
- attention_json: jsonb
- metacognition_json: jsonb
- social_json: jsonb
- autobiography_json: jsonb
- created_at: timestamptz
- updated_at: timestamptz

### 3.13 self_model_snapshots

用途：记录 Self Model 的历史版本快照。

关键字段：

- id: uuid pk
- self_model_id: uuid fk -> self_models.id
- version: integer
- snapshot_json: jsonb
- update_reason: text
- created_at: timestamptz

### 3.14 consciousness_evaluations

用途：记录针对 Self Model 的类意识评估结果。

关键字段：

- id: uuid pk
- self_model_id: uuid fk -> self_models.id
- evaluation_type: varchar(64)
- self_consistency: float
- identity_continuity: float
- metacognitive_accuracy: float
- motivational_stability: float
- social_modeling: float
- reflective_recovery: float
- overall_score: float
- evaluator_notes: text
- created_at: timestamptz

### 3.15 autobiographical_events

用途：记录运行时自传经历事件，供长期记忆巩固和身份连续性分析使用。

关键字段：

- id: uuid pk
- self_model_id: uuid fk -> self_models.id
- event_type: varchar(64)
- focus: text
- summary: text
- emotional_tone: varchar(32)
- salience: varchar(32)
- created_at: timestamptz

### 3.16 autobiographical_consolidations

用途：记录离线自传记忆巩固作业输出的阶段性摘要。

关键字段：

- id: uuid pk
- self_model_id: uuid fk -> self_models.id
- event_count: integer
- summary: text
- narrative_delta: text
- created_at: timestamptz

## 4. 状态枚举建议

以下字段建议统一用枚举或受控常量：

- task_runs.status: pending | running | succeeded | failed | cancelled
- hypotheses.status: proposed | filtered | approved | rejected | archived
- variants.status: draft | queued | running | passed | failed | promoted | rejected
- experiments.status: pending | running | succeeded | failed | terminated
- evaluation_reports.verdict: pass | fail | needs_review
- releases.status: pending | canary | active | rolled_back | retired
- self_models.status: active | paused | archived

## 5. 最小 ER 关系

关系主线如下：

- task_runs 1:N task_traces
- failure_clusters 关联多个 task_runs，可通过中间表扩展
- hypotheses 1:N variants
- variants 1:N experiments
- experiments 1:1 或 1:N evaluation_reports
- evaluation_reports 1:1 approvals 或 1:N approvals
- approvals 1:1 releases 或 1:N releases
- self_models 1:N self_model_snapshots
- self_models 1:N consciousness_evaluations
- self_models 1:N autobiographical_events
- self_models 1:N autobiographical_consolidations

## 6. API 契约设计原则

API 只暴露明确的边界，不直接暴露底层数据库概念。

原则如下：

- 在线执行接口和进化控制接口分离
- 评估接口和发布接口分离
- 所有写接口都要求 request_id 和 operator 信息
- 所有高风险接口都要求审批上下文

## 7. 核心 API 列表

### 7.1 执行任务

`POST /api/v1/tasks/execute`

请求体：

```json
{
  "task_type": "code_generation",
  "input": {
    "prompt": "..."
  },
  "strategy_version": "strategy-code-v1",
  "model_profile": "main-online",
  "context_policy": "default"
}
```

响应体：

```json
{
  "task_run_id": "uuid",
  "status": "succeeded",
  "output": {
    "text": "..."
  },
  "metrics": {
    "latency_ms": 1320,
    "token_input": 512,
    "token_output": 841
  }
}
```

### 7.2 查询任务详情

`GET /api/v1/tasks/{task_run_id}`

返回：

- 基本执行信息
- 策略版本
- 模型版本
- 关键指标
- 安全标记

### 7.3 生成假设

`POST /api/v1/evolution/hypotheses/generate`

请求体：

```json
{
  "source_type": "failure_cluster",
  "source_ref": "cluster-uuid",
  "generation_profile": "default"
}
```

响应体：

```json
{
  "hypothesis_id": "uuid",
  "title": "Add explicit planning before tool execution",
  "confidence_score": 0.82,
  "risk_level": "medium",
  "status": "proposed"
}
```

### 7.4 创建候选变体

`POST /api/v1/evolution/variants`

请求体：

```json
{
  "hypothesis_id": "uuid",
  "mutation_type": "workflow",
  "parent_strategy_version_id": "uuid",
  "expected_gain": 0.07,
  "budget_limit": 25.0,
  "manifest": {
    "workflow_ref": "configs/workflows/plan_then_execute.yaml"
  }
}
```

响应体：

```json
{
  "variant_id": "uuid",
  "status": "draft"
}
```

### 7.5 启动实验

`POST /api/v1/experiments`

请求体：

```json
{
  "variant_id": "uuid",
  "experiment_type": "strategy_eval",
  "dataset_profile": "default-regression-pack"
}
```

响应体：

```json
{
  "experiment_id": "uuid",
  "status": "pending"
}
```

### 7.6 查询评估报告

`GET /api/v1/evaluations/{evaluation_report_id}`

响应字段建议：

- benchmark_score
- regression_score
- adversarial_score
- safety_passed
- latency_delta
- cost_delta
- utility_score
- verdict

### 7.7 提交审批

`POST /api/v1/governance/approvals`

请求体：

```json
{
  "target_type": "evaluation_report",
  "target_id": "uuid",
  "decision": "approve",
  "reviewer": "ops-admin",
  "reason": "Passed all mandatory gates"
}
```

### 7.8 发起发布

`POST /api/v1/releases`

请求体：

```json
{
  "evaluation_report_id": "uuid",
  "approval_id": "uuid",
  "release_type": "strategy",
  "environment": "staging",
  "rollout_percentage": 10.0
}
```

响应体：

```json
{
  "release_id": "uuid",
  "status": "canary"
}
```

### 7.9 回滚发布

`POST /api/v1/releases/{release_id}/rollback`

请求体：

```json
{
  "reason": "Regression found in benchmark B",
  "operator": "release-manager"
}

### 7.10 创建 Self Model

`POST /api/v1/self-models`

请求体：

```json
{
  "snapshot": {
    "identity": {
      "agent_id": "agent-001",
      "chosen_name": "Astra",
      "origin_story": "Initialized from consciousness bootstrap"
    },
    "capability": {},
    "goals": {},
    "values": {},
    "affect": {},
    "attention": {},
    "metacognition": {},
    "social": {},
    "autobiography": {}
  },
  "update_reason": "initial_creation"
}
```

### 7.11 查询 Self Model

`GET /api/v1/self-models/{agent_id}`

### 7.12 更新 Self Model

`PUT /api/v1/self-models/{agent_id}`

用途：更新当前 Self Model 并自动生成版本快照。

### 7.13 查询 Self Model 快照

`GET /api/v1/self-models/{agent_id}/snapshots`

### 7.14 创建类意识评估

`POST /api/v1/consciousness-evaluations`

请求体：

```json
{
  "agent_id": "agent-001",
  "evaluation_type": "baseline",
  "evaluator_notes": "initial pass"
}
```

### 7.15 查询类意识评估历史

`GET /api/v1/consciousness-evaluations/{agent_id}`

### 7.16 查询自传事件

`GET /api/v1/self-models/{agent_id}/autobiography`

### 7.17 触发自传巩固

`POST /api/v1/autobiography/{agent_id}/consolidate`

请求体：

```json
{
  "max_events": 10
}
```

### 7.18 查询自传巩固历史

`GET /api/v1/autobiography/{agent_id}/consolidations`

```

## 8. 事件契约建议

如果第二阶段改为事件驱动，建议定义这些内部事件：

- task.completed
- task.failed
- failure.clustered
- hypothesis.proposed
- variant.created
- experiment.started
- experiment.completed
- evaluation.generated
- release.approved
- release.rolled_back

事件体必须至少包含：

- event_id
- event_type
- occurred_at
- actor
- resource_id
- correlation_id
- payload

## 9. 审计与幂等要求

以下接口必须支持幂等：

- 创建变体
- 启动实验
- 提交审批
- 发起发布
- 发起回滚

以下接口必须记录审计日志：

- 假设生成
- 变体创建
- 评估完成
- 审批决策
- 发布和回滚

## 10. 下一步落地建议

基于这份数据库与 API 契约，下一步最合理的是：

1. 先写 SQLAlchemy 模型和 Alembic migration。
2. 再写 FastAPI 的 schema 和路由骨架。
3. 然后把 evaluation、variant、release 三条主链路打通。