# CogniGuide: AgentTeams 原生的证据驱动元认知学习 Demo

CogniGuide 不让模型仅凭对话猜测学习者的“盲区”。它将已授权、可判分的学习事件和答前置信度，转化为可追溯的学习假设、先修约束路径和人工复核结论。

**本仓库参赛主入口是 [`agentteams/`](agentteams/)**：基于官方 OpsPilot / AgentTeams 基线，使用 `Manager -> 独立 TeamLeader -> 4 个业务 Worker` 的原生协作结构，而不是将 Python workflow 伪装成 AgentTeams。

```text
AgentTeams Manager（仅创建、健康检查、治理）
  -> cogniguide-demo-leader（独立 TeamLeader）
       -> interaction-evidence-analyst
       -> knowledge-state-estimator
       -> learning-path-planner
       -> report-verifier
       -> HTTP 工具网关 / 后续 MCP Server
```

## 当前状态

| 交付项 | 状态 |
| --- | --- |
| AgentTeams 原生 Team、Worker、Skill、共享状态和工具契约 | 已实现 |
| 本地 HTTP 工具网关及授权/证据/路径审计测试 | 已实现 |
| `gpt-5.6-luna` 实际 Responses API 与 Evidence Analyst Worker 合约测试 | 已通过 |
| 真实 AgentTeams Team Room 端到端运行证据 | 需要 Docker Engine 启动后补采集 |

> 当前机器的 Docker Engine 未启动，因此仓库不会把本地 Python 测试写成“已运行真实 AgentTeams”。`cogniguide/` 是确定性参考实现和回归基线，不是参赛主架构。

## 30 秒检查主 Demo 资产

```powershell
cd D:\AIcompetation\agent-infra-competition\agentteams
py -m unittest discover -s tests -v
py tools\mock_tool_server.py --host 127.0.0.1 --port 18089
```

另开一个 PowerShell：

```powershell
Invoke-RestMethod http://127.0.0.1:18089/health
Invoke-RestMethod -Method Post `
  -ContentType 'application/json' `
  -Uri http://127.0.0.1:18089/tools/python_foundations_overconfidence/learning_data.get_task_metadata `
  -Body '{"schema_version":"cogniguide.tool-request/v1","task_id":"CG-1001","trace_id":"smoke-001","actor":"interaction-evidence-analyst"}'
```

随后按照 [`agentteams/AGENTTEAMS_RUNBOOK.md`](agentteams/AGENTTEAMS_RUNBOOK.md) 配置 AgentTeams、创建 Team，并将 [`agentteams/run_demo_task_message.md`](agentteams/run_demo_task_message.md) 中的任务发送到 Team Room 的 `@cogniguide-demo-leader`。

使用当前会话中的受控凭据时，还可执行 `python tools\live_worker_contract.py`：它会直接请求真实 `gpt-5.6-luna`，验证授权聚合与未授权阻断两条 Worker 合约；密钥仅从当前环境变量读取，绝不写入仓库。

## 业务闭环

1. **Interaction Evidence Analyst**：先检查授权，再读取经题库/Rubric 判分的结构化事件，输出 `evidence_refs`。
2. **Knowledge State Estimator**：用登记版本的 BKT 参数、置信度校准误差和 Brier 分数输出“待验证学习假设”。
3. **Learning Path Planner**：在先修知识 DAG 下生成“补前置 -> 练习 -> 复测 -> 反思”的可拒绝建议，并调用路径校验。
4. **Report Verifier**：独立检查授权、证据引用、低样本边界、路径约束和审计，最终只允许 `PUBLISHED`、`NEEDS_MORE_DATA`、`HUMAN_REVIEW_REQUIRED` 或 `BLOCKED`。

关键安全边界：未授权时网关拒绝学习内容读取；原始交互文本和模型思维链不进入共享产物或审计；长期画像写入只能提出审批建议，不能自动执行。

## AgentTeams 资产

| 路径 | 用途 |
| --- | --- |
| [`agentteams/AgentTeam.md`](agentteams/AgentTeam.md) | 原生拓扑与运行边界 |
| [`agentteams/create_agents_messages.md`](agentteams/create_agents_messages.md) | 可直接发送给 Manager 的创建请求 |
| [`agentteams/agents/`](agentteams/agents/) | 四个 Worker 的独立 `Agent.md` |
| [`agentteams/skills/`](agentteams/skills/) | 可复用 Skill 契约 |
| [`agentteams/tools/`](agentteams/tools/) | HTTP mock gateway、工具目录与未来 MCP 映射 |
| [`agentteams/scenarios/`](agentteams/scenarios/) | 授权分析与未授权阻断的可复现场景 |
| [`agentteams/AGENTTEAMS_RUNBOOK.md`](agentteams/AGENTTEAMS_RUNBOOK.md) | Docker / AgentTeams / OpenAI-compatible 模型配置与取证步骤 |

## 研究依据与可扩展方向

- **BKT**：Corbett & Anderson, *UMUAI* 1995；固定 Demo 参数仅用于可解释演示，不宣称已对真实学习者校准。
- **元认知校准**：confidence、Bias、Brier score 与高置信错误；Gutierrez de Blume et al., *JEP* 2022。
- **先修图谱**：人工审核的可追溯 DAG；Pan et al., ACL 2017。
- **SRL 闭环**：计划、监控、反思、再计划；Zimmerman, 2002。
- **后续扩展**：将 HTTP 工具契约映射到 MCP，在真实数据和人工审核基础上引入版本化 RAG、复盘 capsule 和持续评测。

详见 [`docs/research-basis.md`](docs/research-basis.md)、[`docs/architecture.md`](docs/architecture.md) 和 [`方案材料.md`](方案材料.md)。

## 本地确定性参考基线

`cogniguide/` 与根目录的 `run_demo.py` 保留为无 API Key 的确定性回归基线，可验证 BKT、校准、DAG、审计哈希和异常降级逻辑：

```powershell
py -m unittest discover -s tests -v
py run_demo.py --input examples\python_foundations.json --output runs\python-foundations
```

它不负责创建或调度 AgentTeams Worker；真实多 Agent 协作的主证据由 `agentteams/` 的 Team、工具调用 trace、共享 JSON 产物和 Matrix Team Room 记录构成。

## 协作

```powershell
git pull --ff-only
git switch -c your-name/feature
py -m unittest discover -s tests -v
py -m unittest discover -s agentteams/tests -v
git add <明确文件>
git commit -m "Describe the change"
git push -u origin your-name/feature
```

禁止提交 API Key、Manager 密码、真实学习数据、`runs/` 产物或模型思维链。
