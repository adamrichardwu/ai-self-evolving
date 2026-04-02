# Global Workspace 接入执行链路说明

## 1. 目标

这一步的目标不是让 Global Workspace 独立存在，而是让它真正进入在线任务主链路，成为任务执行前的注意力仲裁层。

## 2. 当前接入方式

当前接入采用轻量方式：

- 任务请求进入 API
- 如果带有 agent_id，则读取 Self Model
- 从外部输入、策略上下文、自我关注焦点构造 workspace signals
- Global Workspace 对信号按显著性排序
- 选出 dominant focus 作为当前任务前台焦点
- 任务输出附带 workspace 摘要

## 3. 当前价值

即使还是 MVP，这一步已经让系统具备了三个重要性质：

- 不再完全被动地直接响应输入
- 开始具有内部注意力前台
- 可以把 Self Model 状态影响到当前任务执行

## 4. 下一阶段接入点

后续应继续把以下能力接进 workspace：

- metacognitive alerts
- motivational signals
- retrieved autobiographical memory
- social context signals

## 5. 注意事项

- Workspace 只能影响前台聚焦，不能绕过治理层直接改模型权重
- Workspace 周期结果应写入 trace，后续用于元认知和评估
