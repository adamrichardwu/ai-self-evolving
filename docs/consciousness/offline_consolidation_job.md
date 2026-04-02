# 离线自传巩固作业设计

## 1. 目标

离线巩固作业的目标是把多条运行时自传事件压缩成阶段性生命史摘要，让长期叙事不再完全依赖在线即时更新。

## 2. 当前机制

当前版本已经具备：

1. 收集最近若干条 autobiographical events
2. 提取高频主题
3. 生成 compressed summary
4. 生成 narrative delta
5. 写回 Self Model 的 long-term narrative
6. 记录一次 consolidation run

## 3. 调用方式

当前支持两种触发方式：

- API: `POST /api/v1/autobiography/{agent_id}/consolidate`
- Worker task: `autobiography.consolidate`

## 4. 当前限制

- 主题抽取仍是简单词频
- 还没有跨周期事件聚类
- 还没有社会关系主题压缩

## 5. 下一步

- 引入更稳健的主题归纳器
- 区分短期巩固与长期生命史重写
- 将 consolidation 与 consciousness evaluation 建立联动
