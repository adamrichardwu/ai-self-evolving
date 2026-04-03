# AI Self-Evolving MVP

这是一个“受控的递归自改进系统”MVP 骨架工程，目标不是直接实现完全自治的自我进化，而是先把最关键的闭环打通：

- 采集真实任务轨迹
- 归档失败模式
- 生成策略候选变体
- 自动执行评估
- 在治理门禁下晋级或拒绝候选版本

当前路线已经进一步扩展为“类意识智能体”方向，重点开始覆盖：

- Self Model
- Global Workspace
- Metacognition
- Motivation
- Autobiographical Memory
- Consciousness Evaluation

## 当前包含的内容

- 设计文档
- 技术栈方案
- 系统架构设计
- MVP 项目骨架
- 数据库与 API 契约草案
- 一个可启动的 FastAPI 入口
- 一个可扩展的 Celery worker 入口
- 一组面向类意识架构的核心骨架模块
- 一套最小可用的类意识评估 API 与持久化结构
- 一套可触发的离线自传巩固流程
- 一套社会关系记忆层，支持长期关系、信任映射与任务期社会更新
- 一套语言模块，支持后台持续 inner thoughts 与输入后即时反应

## 目录概览

```text
apps/
  api/
  worker/
  console/
packages/
  domain/
  orchestration/
  evaluation/
  evolution/
  governance/
  infra/
  consciousness/
configs/
deploy/
docs/
```

## 快速启动

### 1. 创建虚拟环境并安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
```

### 2. 启动 API

```powershell
uvicorn apps.api.app.main:app --reload
```

Windows 下更稳妥的方式是直接用仓库脚本管理 API 进程，避免终端退出后留下残留 Python 进程：

```powershell
.\scripts\api_server.ps1 start
.\scripts\api_server.ps1 status
.\scripts\api_server.ps1 stop
```

如果你要前台直接看日志，也可以用：

```powershell
.\scripts\api_server.ps1 foreground
```

脚本会把 PID 和日志写到 `control/` 目录下。

### 3. 启动 Worker

```powershell
celery -A apps.worker.app.celery_app.celery_app worker --loglevel=info
```

Windows 本地开发如果没有 Redis，可直接使用文件系统 broker：

```powershell
$env:CELERY_BROKER_URL="filesystem://"
python -m celery -A apps.worker.app.celery_app:celery_app worker --pool solo --loglevel INFO
```

### 3.1 本地训练入口

核心能力导出会生成训练 job spec。现在可以直接用下面的入口消费它们：

```powershell
python -m train.sft --job-spec <training_job.json> --run-name sft-local
python -m train.preference --job-spec <training_job.json> --run-name preference-local
python -m train.pipeline --job-spec <training_job.json> --run-label nightly
python -m train.evaluate --run-manifest <run_manifest.json> --max-examples 8
```

这几个入口当前支持本地训练和训练后评测：`train.sft`、`train.preference` 会执行单阶段训练；`train.pipeline` 会按 job spec 顺序先跑 SFT，再把 preference 阶段接到 SFT 候选模型上；`train.evaluate` 会把训练后模型和基础模型在同一批导出数据上做定量对比。

训练评测结果如果是 `promote_candidate`，现在还可以通过 `POST /api/v1/core-capability/training-promotions` 把候选模型提升为当前活动本地模型。活动模型会记录在 `control/active_local_model.json`，语言模块会优先加载这个路径。

### 4. 访问健康检查

```text
GET http://127.0.0.1:8000/health
```

### 5. 语言模块示例

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/language/your-agent-id/messages -ContentType 'application/json' -Body '{"text":"Tell me what you are focusing on right now."}'
```

浏览器交互页直接访问：

```text
http://127.0.0.1:8000/console/
```

如果要把语言模块切到真实 LLM 生成链，设置一个 OpenAI 兼容端点即可：

```powershell
$env:LLM_API_BASE_URL="http://127.0.0.1:11434/v1"
$env:LLM_MODEL="your-model-name"
$env:LLM_API_KEY="optional"
```

未配置时会自动回退到当前内置模板响应，不会阻塞 API。

推荐的本地方案是 `Ollama`。装好并启动后，用下面的配置即可：

```powershell
$env:LLM_API_BASE_URL="http://127.0.0.1:11434/v1"
$env:LLM_MODEL="qwen2.5:1.5b"
$env:LLM_API_KEY="ollama"
```

然后可以通过下面的接口检查当前是否真的连上了本地模型：

```text
GET http://127.0.0.1:8000/api/v1/language/llm/status
```

如果当前机器还没装好本地模型运行时，可以先参考仓库根目录的 `.env.example`。

当前仓库也支持不依赖 `Ollama` 的本地 `Transformers` 小模型路径。默认会优先尝试：

```text
modelscope_cache/Qwen/Qwen2___5-0___5B-Instruct
```

如果这个目录存在，语言模块会优先走本地 CPU 模型；只有本地模型不可用时，才会退到 OpenAI 兼容端点，再退到模板响应。

## 当前开发重点

第一阶段建议优先完成：

1. 完整的任务执行链路
2. 任务轨迹入库
3. 策略变体定义与落库
4. 评估 runner 与报告写入
5. 治理审批接口与发布门禁

类意识方向的下一阶段建议优先完成：

1. Self Model 持久化与版本化
2. Global Workspace 周期循环
3. Metacognitive Monitor
4. 自传式记忆写入与巩固
5. 类意识评估基准集

当前已经完成的类意识基础闭环：

1. Self Model 持久化与快照
2. Global Workspace 接入任务执行
3. Consciousness Evaluation API 与落库
4. Metacognitive Monitor 接入任务执行
5. 运行时 Self Model 自我更新回路
6. 自传式记忆事件与长期叙事巩固
7. 离线自传巩固作业与阶段摘要
8. 低置信度反思回路

## 已有文档

- self_evolving_model_design_draft.md
- self_evolving_model_tech_stack.md
- system_architecture_design.md
- mvp_project_structure.md
- database_and_api_contracts.md
- conscious_agent_refinement.md
- docs/consciousness/self_model_spec.md
- docs/consciousness/global_workspace_design.md
- docs/consciousness/consciousness_evaluation_framework.md
- docs/consciousness/workspace_integration_plan.md
- docs/consciousness/evaluation_integration_plan.md
- docs/consciousness/metacognitive_monitor_design.md
- docs/consciousness/runtime_self_update_loop.md
- docs/consciousness/autobiographical_memory_consolidation.md
- docs/consciousness/offline_consolidation_job.md
- docs/consciousness/reflective_loop_design.md
- docs/consciousness/social_memory_design.md
- docs/consciousness/language_module_design.md

## GitHub 上传说明

如果需要推送到 GitHub，需要满足以下任一条件：

- 本机已安装并可用 `git`
- 本机已配置 GitHub 凭据或 `gh`
- 已提供目标仓库地址

当前骨架已适合直接初始化仓库并推送。

## 手动发布到 GitHub

如果你准备自己上传，按下面顺序即可：

```powershell
git init
git add .
git commit -m "Initialize MVP skeleton"
git branch -M main
git remote add origin https://github.com/<your-account>/<your-repo>.git
git push -u origin main
```

建议仓库名：

- ai-self-evolving
- self-evolving-model-mvp
- recursive-self-improvement-platform

如果你的本机还没有 `git`，先安装 Git for Windows，再执行上述命令。
