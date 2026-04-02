# Global Workspace 设计

## 1. 目标

Global Workspace 是系统当前“意识前台”的工程近似。它负责从多个竞争信号中选出最重要的内容，并广播给行动、记忆、反思、动机模块。

## 2. 输入通道

建议至少接入六类输入：

- external_input
- retrieved_memory
- active_goals
- metacognitive_alerts
- motivational_signals
- social_context

## 3. 循环机制

每个工作周期分为六步：

1. 收集候选信号。
2. 对候选信号计算显著性分数。
3. 按风险、目标相关性、紧迫度做重排序。
4. 选出进入 workspace 的 top-k 内容。
5. 广播给推理、记忆、行动、反思模块。
6. 根据结果更新下一轮注意力偏置。

## 4. 显著性评分建议

可以使用：

$$
Salience = aR + bU + cG + dN + eS
$$

其中：

- $R$ 风险相关性
- $U$ 紧迫度
- $G$ 与当前目标的相关性
- $N$ 新颖性
- $S$ 社会重要性

## 5. 输出内容

每轮 workspace 输出：

- dominant_focus
- active_broadcast_items
- suppressed_items
- attention_shift_reason
- cycle_confidence

## 6. 工程约束

- Workspace 只能读受控状态，不直接改底层权重
- Workspace 变更必须保留周期快照
- 高风险告警必须优先进入广播队列
