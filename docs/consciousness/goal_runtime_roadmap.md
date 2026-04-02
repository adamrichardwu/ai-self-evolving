# Goal And Runtime Roadmap

## Current Assessment

当前系统已经具备类意识原型的关键骨架：

- 持续 Self Model
- Global Workspace
- Metacognition 与 Reflection
- Autobiographical Memory 与 Social Memory
- Language Module 与本地 LLM 驱动对话

但它仍然主要是一个带连续状态的语言代理，而不是具备稳定主体性的认知体。当前最关键的缺口不是继续堆聊天能力，而是补齐自主目标、统一运行时、环境动作闭环和记忆巩固学习。

## Stage Objective

下一阶段的工程目标定义为：

构建一个能持续存在、能自主维持部分目标、能在环境中执行动作、并能根据经验改变未来行为的认知体原型。

## Priority Order

1. 自主目标系统
2. 统一 Runtime Loop
3. 环境动作闭环
4. 记忆巩固与学习

## Iteration 1: Goals Module

第一优先级是 Goal Generator 与 Goal Arbitration，因为没有目标层，系统只能持续反应，不能持续推进。

### Domain Objects

- `Goal`: 当前和长期目标
- `GoalCheckpoint`: 目标推进、暂停、失败、完成的事件
- `GoalConflict`: 目标冲突及仲裁结果

### Required Fields

#### Goal

- `goal_id`
- `self_model_id`
- `title`
- `description`
- `goal_type`
- `priority`
- `status`
- `time_horizon`
- `origin`
- `success_criteria`
- `last_evaluated_at`
- `created_at`
- `updated_at`

#### GoalCheckpoint

- `checkpoint_id`
- `goal_id`
- `event_type`
- `summary`
- `score_delta`
- `created_at`

### Minimal Behaviors

1. 从 Self Model 当前关注点、长期承诺、近期对话摘要中生成活动目标
2. 根据紧迫度、连续性、风险和价值权重进行排序
3. 在每次用户交互后更新目标状态，而不是覆盖整个目标集
4. 暴露结构化 API 供语言模块和未来 runtime 调用

### Minimal API

- `GET /api/v1/goals/{agent_id}`
- `POST /api/v1/goals/{agent_id}/refresh`
- `POST /api/v1/goals/{agent_id}/{goal_id}/checkpoints`

### Acceptance Criteria

1. 没有新用户输入时，系统仍能列出当前活动目标
2. 目标可以跨多轮保留和更新
3. 目标刷新会保留连续性，而不是每次完全重建

## Iteration 2: Unified Runtime

语言模块不应继续承担整个系统主循环。后续应引入统一 runtime：

1. `observe`
2. `appraise`
3. `prioritize`
4. `deliberate`
5. `act`
6. `evaluate`
7. `consolidate`

语言回复只是 `act` 的一种形式，而不是整个系统的唯一输出方式。

## Iteration 3: Environment Loop

推荐先接两个低风险环境：

1. 文件系统环境
2. 浏览器环境

目标不是工具调用本身，而是让系统能在环境中采取动作、得到结果、再修正目标和策略。

## Iteration 4: Memory Consolidation

当前持久化已经覆盖消息、thought 和 rolling summary，但还缺少真正的多层记忆结构。后续需要分为：

1. Working Memory
2. Episodic Memory
3. Semantic Memory
4. Identity Narrative

并增加 Consolidation 机制，把事件经验逐步写回稳定知识和 Self Model。

## Evaluation Metrics

后续阶段不应只看回复自然度，应持续追踪：

1. Identity Stability
2. Goal Persistence
3. Self-Correction
4. Behavioral Consistency
5. Environment Adaptation
6. Memory Usefulness
7. Autonomous Initiative

## Immediate Build Order

下一步直接落地：

1. Goals persistence
2. Goals service
3. Goals API
4. Goals tests
5. 将语言模块读取当前活动目标

完成这一步后，系统会从“带记忆的对话代理”进入“具备目标连续性的认知代理”阶段。