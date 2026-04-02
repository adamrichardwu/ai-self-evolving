# Language Module Design

## Goal

语言模块的目标是让系统不只是被动等待请求，而是在后台持续生成内在思考，并在收到用户输入后基于当前内部焦点做出即时反应。

## Runtime Structure

- `language_messages`: 持久化用户与 assistant 对话
- `inner_thoughts`: 持久化后台思考与响应前内部思路
- `language_summaries`: 压缩后的滚动对话记忆
- `LanguageBackgroundLoop`: FastAPI 启动后按固定周期运行
- `send_language_message`: 用户输入进入后触发社会更新、元认知检查、反思判定和响应生成
- `OpenAICompatibleLLM`: 可选的真实生成链，面向本地或远端 OpenAI 兼容接口

## Background Thinking

后台循环每轮会：

1. 读取 Self Model 当前 focus
2. 读取最近用户输入与最近 inner thought
3. 读取社会义务与关系线索
4. 通过 workspace 计算当前 dominant focus
5. 生成一条新的 inner thought 并持久化

## User Reaction

当用户发送语言输入时，系统会：

1. 写入用户消息
2. 更新社会关系记忆
3. 运行 metacognitive monitor
4. 运行 reflective loop
5. 生成 reaction thought
6. 生成 assistant reply
7. 更新滚动对话摘要
8. 写回 Self Model 的当前 focus 与 metacognition

## Real Generation Path

当以下配置存在时，语言模块会优先走真实 LLM：

- `LOCAL_MODEL_PATH` 可选，本地 `Transformers` 模型目录
- `LLM_API_BASE_URL`
- `LLM_MODEL`
- `LLM_API_KEY` 可选

优先级如下：

1. `LOCAL_MODEL_PATH` 指向的本地模型目录
2. OpenAI 兼容 `POST /chat/completions`
3. 模板式 thought/response 降级

当上层路径不可达或未配置时，系统自动回退到下一层，不中断主流程。

## Rolling Summary

语言状态接口会返回一个滚动摘要，用于保存最近几轮对话的压缩记忆，避免系统只依赖原始 message log。

## API Surface

- `GET /api/v1/language/llm/status`
- `POST /api/v1/language/{agent_id}/messages`
- `POST /api/v1/language/{agent_id}/think`
- `GET /api/v1/language/{agent_id}/state`

## Limitations

- 当前仍是启发式语言反应，不是真实语义生成模型
- 后台思考频率固定，尚未按任务紧张度自适应
- 还没有多轮 conversation summary 压缩