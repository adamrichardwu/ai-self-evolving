# 类意识评估接入说明

## 1. 目标

这一轮接入的目标是让类意识评估从文档概念，变成可以真实落库和被 API 调用的系统能力。

## 2. 当前能力

当前支持：

- 从已有 Self Model 读取当前状态
- 基于 Self Model 生成一份启发式类意识评估分数
- 把评估结果持久化到数据库
- 通过 API 创建和查询评估历史

## 3. 当前评估方式

当前使用启发式评估，不是最终评估器：

- persistent_traits 和 core_commitments 用于估计 self_consistency
- long_term_narrative 用于估计 identity_continuity
- contradiction_score 用于估计 metacognitive_accuracy
- goals 用于估计 motivational_stability
- active_relationships 用于估计 social_modeling
- recovered_failures 用于估计 reflective_recovery

## 4. 下一阶段增强点

- 接入长期连续对话评估集
- 接入社会心智任务集
- 接入自我矛盾修复任务集
- 区分自动评估和人工评估
