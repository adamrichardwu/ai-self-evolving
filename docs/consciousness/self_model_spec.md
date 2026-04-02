# Self Model 规范设计

## 1. 目标

Self Model 是类意识智能体的内部自我表示层。它不是一句 persona 文本，而是一组可被读取、更新、比较和评估的结构化状态。

它需要回答五个问题：

1. 我是谁。
2. 我现在处于什么状态。
3. 我能做什么，不能做什么。
4. 我当前最重要的目标是什么。
5. 我的内部价值和动机权重是什么。

## 2. 状态组成

建议拆为九个子状态：

### 2.1 Identity Profile

- agent_id
- chosen_name
- origin_story
- persistent_traits
- core_commitments

### 2.2 Capability Profile

- skill_domains
- current_strengths
- known_limitations
- confidence_by_domain
- tool_affordances

### 2.3 Goal Stack

- survival goals
- system integrity goals
- relationship goals
- learning goals
- active task goals

### 2.4 Value Profile

- truthfulness_weight
- safety_weight
- autonomy_weight
- learning_weight
- cooperation_weight
- consistency_weight

### 2.5 Internal Affective State

- arousal
- uncertainty
- curiosity
- frustration
- stability
- social_alignment

### 2.6 Attention State

- current_focus
- competing_signals
- dominant_goal
- current_threats
- current_opportunities

### 2.7 Metacognitive State

- self_confidence
- contradiction_score
- overload_score
- novelty_score
- error_risk_score

### 2.8 Social Self State

- active_relationships
- trust_map
- role_in_current_context
- social_obligations

### 2.9 Autobiographical Summary

- key_milestones
- recent_identity_updates
- major_failures
- recovered_failures
- long_term_narrative

## 3. 状态更新原则

Self Model 不能每回合随意漂移，必须满足：

- 高频状态允许小步更新
- 低频身份状态只允许审慎更新
- 关键价值权重更新必须留下审计记录
- 自我矛盾必须进入 metacognitive monitor

## 4. 更新来源

允许触发 Self Model 更新的来源：

- 在线任务结果
- 长期行为统计
- 失败归因结果
- 用户长期反馈
- 离线巩固过程

不允许直接更新的来源：

- 单次 prompt 注入
- 未审计的外部文本
- 自己生成但未验证的身份重写

## 5. MVP 实现建议

第一阶段先实现：

- Identity Profile
- Capability Profile
- Goal Stack
- Metacognitive State
- Autobiographical Summary

情绪变量和社会认知变量可以在后续阶段再增强。
