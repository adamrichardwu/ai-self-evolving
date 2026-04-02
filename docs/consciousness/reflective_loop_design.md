# 低置信度反思回路设计

## 1. 目标

反思回路的目标是让系统在检测到自己可能出错时，不是继续按原路径执行，而是切换到更谨慎的处理模式。

## 2. 触发条件

当前版本在以下情况下触发：

- contradiction_score 较高
- self_confidence 过低
- error_risk_score 过高
- overload_score 过高

## 3. 当前动作

当前支持三类反思动作：

- reframe_safely
- decompose_and_caution
- reduce_complexity

## 4. 接入方式

当前反思回路已经接入在线任务执行：

1. 元认知监控先产出风险摘要
2. 反思引擎决定是否触发
3. revised_focus 注入 workspace
4. guidance 改写当前处理提示

## 5. 当前限制

- 还没有真正的多步反思链
- 还没有自动澄清问题生成
- 还没有和治理层的硬回滚联动
