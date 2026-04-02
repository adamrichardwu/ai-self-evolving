# 自我进化模型技术栈设计

## 1. 设计目标

这份技术栈方案基于现有设计稿，目标不是堆叠热门组件，而是为“受控的递归自改进系统”选出一套可落地、可扩展、可审计的工程组合。

技术栈设计遵循四个约束：

1. 第一阶段必须能快速验证策略级自优化闭环。
2. 第二阶段必须能平滑引入轻量训练与评估自动化。
3. 第三阶段必须支持多版本并行实验、治理与回滚。
4. 全过程必须保留审计能力，避免系统绕过评估直接演化。

## 2. 总体选型原则

本方案推荐采用：

- Python 作为核心 AI 编排与训练语言。
- TypeScript 作为控制台、运维界面和轻服务层语言。
- 容器化部署作为实验隔离和环境复现的基础。
- 面向事件的任务流作为进化闭环的主调度模式。
- 模块化数据与模型注册体系作为治理基础。

不建议第一阶段采用：

- 完全自研深度训练框架
- 过早引入复杂 Kubernetes operator
- 过早追求多云抽象
- 直接依赖单一闭源平台完成全部闭环

原因很直接：第一阶段重点是证明闭环成立，而不是把基础设施做成平台产品。

## 3. 推荐技术栈总览

### 3.1 语言与运行时

- Python 3.11：核心 agent 编排、训练、评估、数据处理。
- TypeScript + Node.js 22：管理后台、实验面板、审批流、配置服务。
- Bash/PowerShell：运维脚本与本地自动化。

### 3.2 核心 AI 框架

- PyTorch：训练与推理主框架。
- Hugging Face Transformers：基座模型加载、微调、推理适配。
- PEFT：LoRA、Adapter 等轻量参数高效微调。
- TRL：偏好优化、奖励模型、对齐类训练扩展。
- vLLM：高吞吐推理服务，适合多候选评估和批量实验。

### 3.3 工作流与 Agent 编排

- LangGraph：适合构建有状态、可回溯的 agent 工作流图。
- Pydantic v2：统一状态对象、配置对象和实验契约校验。
- FastAPI：暴露控制接口、评估触发接口、内部服务 API。
- Celery 或 Prefect：异步任务执行与实验调度。

### 3.4 数据与存储

- PostgreSQL：结构化元数据、实验记录、审批记录、版本索引。
- MinIO 或 S3：数据集、模型制品、评估报告、日志归档。
- Qdrant：向量记忆检索。
- Neo4j：结构记忆、依赖图、模块关系图。
- Redis：任务队列缓存、短期状态、速率限制。

### 3.5 MLOps 与实验管理

- MLflow：实验追踪、参数记录、模型注册。
- DVC：数据集与评估集版本管理。
- Weights & Biases 可选：若团队更重视可视化实验对比。

### 3.6 监控与可观测性

- OpenTelemetry：链路追踪与标准化遥测。
- Prometheus：指标采集。
- Grafana：可视化监控面板。
- Loki：日志聚合。

### 3.7 安全与治理

- OPA：策略判断与发布门禁。
- Vault：密钥、令牌、模型仓访问凭据管理。
- GitHub Actions 或 Azure DevOps：评估门禁、签名与发布流水线。

### 3.8 基础设施

- Docker：实验与服务隔离基础。
- Kubernetes：第二阶段后用于作业编排、资源隔离、灰度发布。
- NVIDIA Container Toolkit：GPU 工作负载容器化。
- Argo Workflows 可选：批量训练/评估流水线编排。

## 4. 分层技术映射

### 4.1 基础执行模型层

推荐组合：

- 推理主模型：支持 API 模型或本地开源模型双轨制。
- 本地推理框架：vLLM。
- 模型包装层：Transformers + Pydantic 契约。

建议：

- Phase 1 先允许 API 大模型 + 本地小模型混合运行。
- Phase 2 开始把高频实验对象迁移到本地开源模型，降低迭代成本。

候选模型组合：

- 主推理模型：通用大模型 API 或 Qwen/Llama 系列指令模型。
- 评估/分类小模型：7B 以下开源模型或专用分类器。
- reranker：BGE reranker 或 cross-encoder 类模型。

原因：

- 第一阶段需要能力上限高的主模型，快速验证闭环。
- 评估与路由任务不应该占用昂贵主模型。

### 4.2 记忆与知识层

推荐组合：

- 向量记忆：Qdrant
- 文档知识仓：PostgreSQL + MinIO
- 结构记忆：Neo4j
- 检索编排：Python 自研 service + embedding pipeline

为什么不是单独只用向量库：

- 情节记忆适合向量检索。
- 语义知识适合结构化版本存储。
- 结构记忆更适合图关系查询。

这三者混合，才符合原设计稿中的三层记忆划分。

### 4.3 自我监控层

推荐组合：

- OpenTelemetry 埋点到每次任务执行
- Prometheus 采集成功率、耗时、成本、失败率
- Loki 聚合原始日志
- PostgreSQL 保存任务结果摘要和告警记录

关键监控字段：

- task_id
- model_version
- strategy_version
- evaluation_profile
- cost_tokens
- latency_ms
- tool_error_count
- user_feedback_score
- safety_flag

### 4.4 假设生成层

推荐组合：

- LangGraph 组织假设生成流程
- 主模型负责解释失败模式与提出候选改进方向
- 规则引擎负责硬约束过滤
- PostgreSQL 记录假设来源、置信度、审批状态

这里不建议一开始就做全自动黑箱搜索，而应采用“模型生成假设 + 规则筛掉危险改动”的混合模式。

### 4.5 变体生成层

推荐组合：

- 配置模板引擎：Jinja2 或 Pydantic 配置生成
- Prompt/策略版本化：Git + PostgreSQL 索引
- 训练变体定义：YAML/JSON Schema + Pydantic 校验

每个候选变体至少要有以下字段：

- variant_id
- parent_version
- mutation_type
- expected_gain
- budget_limit
- risk_level
- rollback_condition

### 4.6 训练与实验层

推荐组合：

- PyTorch + PEFT：轻训练主链路
- TRL：偏好学习与奖励建模
- MLflow：实验追踪与模型登记
- DVC：训练集、验证集、对抗集版本管理
- Celery/Prefect：训练作业投递与状态回传
- Docker：实验隔离

如果算力资源较稳定，第二阶段建议引入：

- Kubernetes Job 或 Argo Workflows
- 独立 GPU 队列
- 实验资源配额控制器

### 4.7 评估与裁决层

推荐组合：

- pytest + 自定义评估 runner：执行基准、回归、对抗测试
- FastAPI 评估服务：统一入口
- PostgreSQL：记录各维度分数
- MLflow：关联实验版本与评估结果
- OPA：把“准入规则”写成可审计策略

这里的核心不是评估脚本本身，而是“评估规则不能被候选变体自己修改”。

### 4.8 治理与发布层

推荐组合：

- GitHub Actions/Azure DevOps：流水线门禁
- MLflow Model Registry：候选模型登记
- OPA：发布策略检查
- Vault：签名与访问控制
- Kubernetes 灰度发布或 API 路由切流

治理层最重要的三个动作：

- 审批
- 签名
- 回滚

## 5. 推荐架构实现方案

## 5.1 MVP 方案

适用阶段：Phase 1

推荐组合：

- Python 单体后端：FastAPI + LangGraph + Celery
- PostgreSQL
- Redis
- Qdrant
- MinIO
- MLflow
- Docker Compose

这一套足够支撑：

- 任务采集
- 失败聚类
- 策略候选生成
- 自动评估
- 最优策略晋级

优点：

- 上手快
- 架构简单
- 易调试
- 成本可控

缺点：

- 横向扩展一般
- 多团队协作边界不够清晰

### 5.2 成长型方案

适用阶段：Phase 2

推荐组合：

- Python 服务拆分为：orchestrator、trainer、evaluator、memory-service
- TypeScript 管理后台
- Kubernetes
- MLflow + DVC
- Prometheus + Grafana + Loki
- OPA + Vault

这一阶段开始形成清晰的“实验系统”和“生产系统”隔离。

### 5.3 平台化方案

适用阶段：Phase 3

推荐组合：

- 事件总线：Kafka 或 NATS
- 工作流：Argo Workflows 或 Temporal
- GPU 调度：Kubernetes + Volcano 可选
- 图谱记忆：Neo4j
- 统一元控制器服务
- 多租户实验平台

这时系统已经从一个 AI 应用，升级为一个“自演化 AI 平台”。

## 6. 模型策略建议

### 6.1 第一阶段模型策略

推荐：

- 主模型用强能力 API 模型，提高假设生成与策略对比质量。
- 检索、分类、评分尽量本地化，降低推理成本。
- 不训练基座，只对策略、工作流和 prompt 变体做自动实验。

### 6.2 第二阶段模型策略

推荐：

- 主模型逐步切换到可控的开源底座。
- 对高价值垂直领域使用 LoRA。
- 对评估器、reranker、错误分类器使用小模型专训。

### 6.3 第三阶段模型策略

推荐：

- 引入多模型协作，不让一个模型同时扮演生成者、评审者和裁决者。
- 引入蒸馏和专家路由，降低长期成本。

## 7. 数据与制品规范

建议从第一天开始定义统一目录规范。

建议的对象分类：

- datasets：训练集、验证集、红队集、回归集
- models：基座模型、LoRA、评估模型、reranker
- variants：prompt、workflow、routing、config
- reports：评估报告、风险报告、发布记录
- traces：任务轨迹、错误日志、反馈数据

建议的版本规则：

- 基座模型版本独立编号
- 策略版本独立编号
- LoRA/adapter 版本独立编号
- 发布版本必须引用完整依赖树

## 8. 安全栈建议

你的系统如果真的要“自我进化”，安全栈不能是附属品，必须和训练栈同级建设。

推荐最小安全组合：

- OPA：定义发布策略、资源上限策略、审批策略
- Vault：保存 API key、模型仓凭据、签名密钥
- 审计日志：所有变体生成、评估、晋级、回滚都记录
- 沙箱执行：训练、评估、红队任务都在隔离容器中运行

必须禁止：

- 候选变体修改评估器代码后直接参与自评
- 候选变体直接访问生产评估集
- 候选变体绕过审批变更资源阈值

## 9. 团队开发栈建议

如果你要真的做出来，而不是只写方案，建议开发栈也标准化。

推荐：

- Python 包管理：uv 或 Poetry
- 代码质量：ruff + black + mypy
- 测试：pytest
- TypeScript 质量：pnpm + eslint + typescript
- API 契约：OpenAPI
- 文档：Markdown + MkDocs

原因：

- AI 系统的复杂度会很快超过直觉。
- 没有类型、测试、版本和契约，后续演化会先把工程本身搞乱。

## 10. 最终推荐组合

如果现在就开始做，我建议采用下面这套“最稳妥且可扩展”的组合：

- 后端：Python 3.11 + FastAPI + LangGraph + Celery
- 训练：PyTorch + Transformers + PEFT + TRL
- 推理：vLLM
- 数据：PostgreSQL + Redis + MinIO + Qdrant + Neo4j
- 实验：MLflow + DVC
- 监控：OpenTelemetry + Prometheus + Grafana + Loki
- 治理：OPA + Vault + GitHub Actions
- 基础设施：Docker，第二阶段升级 Kubernetes
- 前端控制台：Next.js 或 React + TypeScript

这是因为这套栈满足三个关键条件：

- 足够快，能做 MVP。
- 足够稳，能做审计和回滚。
- 足够扩，能从策略演化走到参数演化，再走到系统级递归改进。

## 11. 下一步建议

基于这份技术栈方案，最自然的下一步有三种：

1. 我继续帮你画一版系统架构图，把各服务关系和数据流画出来。
2. 我继续帮你写 MVP 目录结构和模块拆分，直接进入工程初始化级别。
3. 我继续帮你设计数据库表和核心 API 契约，把这套栈落到实现细节。