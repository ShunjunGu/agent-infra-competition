# CogniGuide 架构与安全边界

## 1. 设计目标

CogniGuide 的目标不是用大模型给学习者贴“认知盲区”标签，而是构建一个可复用的学习分析工作流：每条建议都可回溯到**可判分学习事件、模型状态、先修关系、路径决策和验证规则**。

这使它可以服务企业培训、岗位能力提升和知识工作流，而非只是一轮个人聊天。

## 2. 原生 AgentTeams 层与确定性参考基线

| 层 | 当前状态 | 责任 |
| --- | --- | --- |
| `agentteams/` 原生参赛 Demo | 资产和本地工具网关已测试；真实 Team Room 待 Docker 环境验证 | 由 Manager 创建独立 TeamLeader、4 个 Worker、Skill、共享状态和工具调用；Worker/TeamLeader 负责真实协作 |
| `cogniguide/` 本地确定性参考基线 | 已测试 | 计算/审计逻辑的无 API Key 回归验证，不创建或编排 AgentTeams Worker |

两层共享业务角色、输入输出契约和安全策略，但职责不能倒置：`cogniguide/` 不伪装为 AgentTeams 运行证据，也不应被 Worker 当作“一次调用就完成全部多 Agent 工作”的工具。`agentteams/` 内的网关只提供最小的数据、框架、验证和审计能力，TeamLeader/Worker 才是协作主体。

## 3. 状态机

```text
RECEIVED
  -> CONSENT_CHECKED
  -> EVIDENCE_PROFILED
  -> KNOWLEDGE_STATE_ESTIMATED
  -> PATH_PLANNED
  -> VERIFIED
  -> PUBLISHED

CONSENT_CHECKED -> BLOCKED                 # 未授权
KNOWLEDGE_STATE_ESTIMATED -> NEEDS_MORE_DATA  # 每概念少于 3 条可判分证据
VERIFIED -> HUMAN_REVIEW_REQUIRED          # 低样本、隐私发现、校准异常
```

在真实 AgentTeams 部署中，Manager 不进入业务 Team Room；独立 TeamLeader 只负责路由和状态转换；业务结论由 Worker 的结构化产物输出；Verifier 不允许无证据结论发布。

## 4. 业务 Agent 与状态契约

| Agent | 输入 | 输出 | 失败/降级 |
| --- | --- | --- | --- |
| Consent Boundary Agent | 授权与导入摘要 | `policy` | 未授权立即 `BLOCKED`，不分析内容 |
| Interaction Evidence Analyst | 结构化评估事件、辅助交互元数据 | `interaction_profile` | 未知概念/非法置信度拒绝输入 |
| Knowledge State Estimator | 证据画像、BKT 参数 | `knowledge_state` | 低样本只产生待补证据请求 |
| Learning Path Planner | 知识状态、先修 DAG | `learning_plan` | 图不合法时禁止产出路径 |
| Report Verifier | 以上产物 | `report`、人工复核标记 | 缺证据/越权/不安全声明拒绝发布 |

关键状态均为 JSON；下游不依赖自然语言摘要作为事实源。

## 5. 评估与学习闭环

首版使用预先判分的 `learning_signals`，每个事件包含：

```json
{
  "concept": "functions",
  "observed_correct": false,
  "confidence": 0.9,
  "evidence_id": "exercise-functions-01",
  "question_type": "debug"
}
```

生产化时，Assessment Evidence Agent 应通过版本化题库/Rubric 或受控评分工具生成 `observed_correct`；不应由一个无证据的 LLM 自行决定对错。

学习路径遵循：

```text
计划（选定目标与可判分任务）
  -> 监控（答题结果 + 答前 confidence）
  -> 反思（预测与实际的差异）
  -> 复测（新事件）
  -> 重规划（更新知识状态和下一阶段）
```

`run_closed_loop_demo.py` 演示的是**模型状态按新证据更新**，不是对真实学习效果的因果证明。

## 6. 数据、隐私和安全

- 每次分析必须显式 `consent.analysis_authorized=true`；
- 报告不复述原始交互文本，只保留结构化证据 ID；
- 发现邮箱或手机号模式时标记人工复核；
- `runs/` 不入库，避免提交学习数据；
- 审计记录保存状态变更、哈希、调用结果和证据索引，不保存模型思维链；
- 建议均为可拒绝、可修改的学习建议，不触发任何高风险自动决策。

## 7. 工具/MCP 与运行证据

工具目录使用 HTTP gateway 作为可本地复现的 MCP 前置契约：每次调用携带 `schema_version`、`task_id`、`trace_id` 和 `actor`，并在网关侧检查角色最小权限。未来生产化时可不改业务 Skill 地映射到 MCP Server。

完整运行证据应包括：Worker/TeamLeader 创建与健康检查记录、Team Room 中的协作消息、每个 Worker 的结构化 JSON 产物、工具 trace/audit、以及最终的验证状态。当前环境 Docker Engine 未启动，因此仓库仅声称已验证工具网关和确定性基线；不得将其表述为已完成真实 AgentTeams Team Room 运行。

## 8. 竞赛价值

本设计把“多 Agent 协同”落到可审计系统能力：角色隔离、结构化上下文、可替换 Skill、验证门、异常分支、完整性证明和人工确认，而不是把多个 Prompt 串起来。
