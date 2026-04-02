# 自我进化模型 MVP 目录结构与模块拆分

## 1. MVP 目标

第一阶段 MVP 只解决一件事：让系统能够围绕策略级变体形成闭环。

也就是说，MVP 要做到：

- 采集任务轨迹
- 聚类失败模式
- 生成 prompt 或 workflow 候选
- 自动评估候选表现
- 选择更优策略进入下一版本

这一阶段不做：

- 基座模型重训练
- 复杂多代理自治重构
- 自动改写治理规则
- 在线直接自升级

## 2. 推荐项目结构

```text
ai-self-evolving/
  apps/
    api/
      app/
        main.py
        core/
        routes/
        schemas/
        services/
      tests/
    worker/
      app/
        celery_app.py
        jobs/
        tasks/
      tests/
    console/
      src/
      public/
  packages/
    domain/
      models/
      value_objects/
      enums/
      policies/
    orchestration/
      graphs/
      nodes/
      state/
    memory/
      episodic/
      semantic/
      structural/
    evaluation/
      runners/
      benchmarks/
      regressions/
      adversarial/
    evolution/
      hypotheses/
      variants/
      selectors/
    telemetry/
      traces/
      metrics/
      alerts/
    governance/
      approvals/
      release/
      rollback/
      policies/
    infra/
      db/
      queue/
      storage/
      model/
  configs/
    app/
    prompts/
    workflows/
    evaluation/
    policies/
  datasets/
    benchmark/
    regression/
    adversarial/
    failure_cases/
  reports/
    evaluation/
    release/
  scripts/
  deploy/
    docker/
    compose/
    k8s/
  docs/
  pyproject.toml
  pnpm-workspace.yaml
  README.md
```

## 3. 目录设计原则

这里采用 apps + packages 的原因是：

- apps 表示可运行入口
- packages 表示领域能力模块
- configs 和 datasets 作为受版本控制的演化输入
- reports 作为审计输出

这样结构清晰，后续拆微服务时不会重做包边界。

## 4. Apps 层拆分

### 4.1 apps/api

职责：

- 对外提供任务执行接口
- 提供候选评估触发接口
- 提供版本查询、实验查询和健康检查接口

建议模块：

- routes：HTTP 路由
- schemas：Pydantic 请求响应对象
- services：应用层编排
- core：配置、日志、鉴权、依赖注入

### 4.2 apps/worker

职责：

- 执行异步实验任务
- 跑失败聚类、候选生成、自动评估
- 调用训练和评估 runner

建议模块：

- celery_app.py：Celery 初始化
- jobs：高层作业定义
- tasks：细粒度任务单元

### 4.3 apps/console

职责：

- 展示任务表现与版本对比
- 展示失败模式聚类结果
- 展示候选变体与审批状态
- 提供灰度和回滚操作入口

建议技术：

- React 或 Next.js + TypeScript

## 5. Packages 层拆分

### 5.1 packages/domain

这是整个项目的稳定内核，主要放：

- TaskRun
- StrategyVersion
- ModelVersion
- Hypothesis
- Variant
- EvaluationReport
- ReleaseRecord

要求：

- 不依赖具体框架
- 保持纯领域对象表达

### 5.2 packages/orchestration

职责：

- 定义任务执行图
- 组织模型调用、工具调用和记忆调用
- 维护 state machine

子模块建议：

- graphs：LangGraph 工作流图
- nodes：任务节点实现
- state：共享状态结构

### 5.3 packages/memory

职责：

- 封装情节记忆、语义记忆、结构记忆
- 统一 embedding、索引、写回接口

子模块建议：

- episodic：任务轨迹写入与检索
- semantic：经验提炼与语义检索
- structural：模块图谱与依赖查询

### 5.4 packages/evaluation

职责：

- 管理评估执行器
- 组织 benchmark、regression、adversarial 集
- 生成统一评分结果

子模块建议：

- runners：评估运行器
- benchmarks：标准任务集
- regressions：回归任务集
- adversarial：对抗任务集

### 5.5 packages/evolution

职责：

- 失败分析
- 假设生成
- 变体生成
- 候选选择

子模块建议：

- hypotheses：失败模式到假设生成
- variants：从假设生成配置化变体
- selectors：候选排序与晋级建议

### 5.6 packages/telemetry

职责：

- trace 采集与解析
- metric 聚合
- 告警摘要输出

### 5.7 packages/governance

职责：

- 审批模型
- 发布门禁
- 回滚决策
- OPA 策略适配

### 5.8 packages/infra

职责：

- PostgreSQL、Redis、Qdrant、MinIO 等基础依赖接入
- 统一 repository 和 provider 封装

## 6. 核心模块依赖方向

依赖方向必须保持单向：

- apps -> packages
- orchestration/evolution/evaluation/governance -> domain
- infra 为外部依赖适配层
- domain 不反向依赖任何具体实现

这很重要，因为后期一旦开始做真正的“系统级自进化”，如果领域层和基础设施耦合，会非常难改。

## 7. MVP 核心流程对应模块

### 7.1 在线执行流程

- apps/api 接收请求
- packages/orchestration 执行任务图
- packages/memory 提供上下文与经验检索
- packages/telemetry 写入轨迹与指标

### 7.2 离线进化流程

- apps/worker 拉取失败任务摘要
- packages/evolution 生成假设和候选变体
- packages/evaluation 运行自动评估
- packages/governance 给出晋级建议

## 8. 最小实现优先级

第一批必须先写的模块：

1. domain
2. orchestration
3. telemetry
4. evaluation
5. evolution
6. infra

第二批再写：

1. governance
2. console
3. 结构记忆图谱

## 9. MVP 必要文件清单

如果你马上开始初始化项目，建议至少先创建这些文件：

- apps/api/app/main.py
- apps/worker/app/celery_app.py
- packages/domain/models/task_run.py
- packages/domain/models/variant.py
- packages/orchestration/graphs/main_graph.py
- packages/evaluation/runners/strategy_runner.py
- packages/evolution/hypotheses/generator.py
- packages/evolution/variants/factory.py
- packages/governance/approvals/service.py
- packages/infra/db/session.py
- configs/prompts/base_prompt.yaml
- configs/workflows/default_workflow.yaml
- configs/evaluation/default_profile.yaml

## 10. 推荐初始化顺序

按下面顺序做最稳：

1. 先把 domain 和 infra 打底。
2. 再把 api、orchestration、telemetry 串起来。
3. 然后补上 evaluation 和 evolution。
4. 最后再接 governance 和 console。

## 11. 一句话建议

MVP 不要一开始就做成微服务迷宫，先保持“单仓、多包、少服务、强边界”的结构，等闭环跑通后再拆服务。