# Social Memory Design

## Goal

社会关系记忆层用于把“他者”从一次性输入提升为长期社会对象。它补齐当前类意识架构里 `SelfModel.social` 只有投影、没有独立记忆源的问题。

## Core Model

- `social_relationships`：面向单个 agent 的长期关系记录
- `counterpart_id`：对方的稳定标识
- `relationship_type`：用户、操作者、协作者、评估者等角色类型
- `trust_score`：当前信任估计
- `familiarity_score`：熟悉度估计
- `interaction_count`：交互次数
- `last_interaction_summary`：最近一次互动摘要
- `role_in_context`：当前情境中的社会角色
- `social_obligations_json`：该关系诱发的义务与承诺

## Runtime Flow

1. API 或任务执行收到 `social_context`
2. 社会记忆引擎更新 trust/familiarity/obligations
3. `SelfModel.social` 同步为投影层
4. 同一轮 runtime self update 将新社会状态纳入快照

## Initial Heuristics

- 正向互动小幅提高 `trust_score`
- 敌对或紧张互动降低 `trust_score`
- 每次互动都增加 `familiarity_score`
- 义务列表做去重合并
- `active_relationships` 使用名称优先、标识回退的方式投影

## API Surface

- `POST /api/v1/social-memory/{agent_id}/relationships`
- `GET /api/v1/social-memory/{agent_id}/relationships`
- `GET /api/v1/social-memory/{agent_id}/relationships/{counterpart_id}`

## Next Step

下一步可以把社会关系进一步扩展到：

- 多主体网络图
- 长期联盟/冲突轨迹
- 社会预测与期望违背检测
- 社会关系对动机与反思回路的权重调制