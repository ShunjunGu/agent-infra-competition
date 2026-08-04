# CogniGuide AgentTeams 原生 Demo

这里是 CogniGuide 的主多 Agent Demo：由 **AgentTeams Manager、独立 TeamLeader
和四个 Worker** 完成创建、协作、状态传递和发布门禁。它不是把角色顺序写死在本地
workflow 中；`tools/` 只作为 AgentTeams Worker 调用的 HTTP 数据/验证网关，不负责任
何 Agent 路由或决策。

```text
Manager
  -> cogniguide-demo Team
       -> cogniguide-demo-leader (独立 TeamLeader)
            -> interaction-evidence-analyst
            -> knowledge-state-estimator
            -> learning-path-planner
            -> report-verifier
```

## 从这里开始

1. 阅读 [`AgentTeam.md`](AgentTeam.md) 了解角色边界、共享 JSON 产物和终态。
2. 启动网关：`run_gateway.bat`，再确认 `GET /health` 与 `GET /scenarios`。
3. 按 [`AGENTTEAMS_RUNBOOK.md`](AGENTTEAMS_RUNBOOK.md) 配置 Docker、AgentTeams、
   Matrix/Element 和本地受控模型凭据。
4. 将 [`create_agents_messages.md`](create_agents_messages.md) 发送给 Manager；其中
   `<MOCK_TOOL_BASE_URL>` 必须替换为从 Worker 容器内验证过的网关地址。
5. 在新建 Team Room 中发送 [`run_demo_task_message.md`](run_demo_task_message.md) 的
   两条任务，保留 Team 协作、工具 trace、审计和 JSON 产物作为评审证据。

所有 POST 工具调用均须包含 `schema_version=cogniguide.tool-request/v1`、`task_id`、
`trace_id` 和当前 Worker 的 `actor`。网关会在数据读取前执行场景范围、角色最小权限
和授权边界校验；完整格式见 [`tools/tool_catalog.json`](tools/tool_catalog.json)。

## 目录说明

| 路径 | 用途 |
| --- | --- |
| [`agents/`](agents/) | 四个 AgentTeams Worker 的可审计角色契约 |
| [`skills/`](skills/) | 可复用 Skill 定义 |
| [`tools/`](tools/) | HTTP mock tool gateway；没有编排逻辑 |
| [`scenarios/`](scenarios/) | 已授权和未授权的可复现实验夹具 |
| [`MCP_MAPPING.md`](MCP_MAPPING.md) | mock HTTP contract 到生产 MCP contract 的迁移边界 |
| [`team_spec.json`](team_spec.json) | Team 设计与状态协议摘要 |
| [`task_state.example.json`](task_state.example.json) | 共享任务状态样例 |

## 最小验收

- `python_foundations_overconfidence`：四个 Worker 通过独立 TeamLeader 传递 JSON
  产物；函数概念的高置信错误具备 `evt-functions-*` 证据；先修路径经工具验证；
  因低样本/校准不确定性进入审慎状态。
- `consent_required`：先读 metadata，返回 `BLOCKED`；gateway trace 中不得出现
  `learning_data.get_assessment_events` 或 `learning_data.get_interaction_observations`。

## 真实运行边界

本地 gateway 测试证明的是工具契约。只有 Docker 已运行、AgentTeams Worker 全部健康、
独立 TeamLeader 已创建，且 Team Room 和容器侧 gateway 调用可见时，才可以声明完成了
真实 AgentTeams 运行。API Key 始终只存放于本机受控配置，不写入仓库。
