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

### 3. 启动 Worker

```powershell
celery -A apps.worker.app.celery_app.celery_app worker --loglevel=info
```

Windows 本地开发如果没有 Redis，可直接使用文件系统 broker：

```powershell
$env:CELERY_BROKER_URL="filesystem://"
python -m celery -A apps.worker.app.celery_app:celery_app worker --pool solo --loglevel INFO
```

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
