# 评测与运行证据

## 已自动化验证

```powershell
py -m unittest discover -s tests -v
py -m unittest discover -s agentteams/tests -v
```

| 用例 | 验证目标 |
| --- | --- |
| 完整主路径 | Team Leader 与 4 个角色按顺序留下结构化 trace，函数概念产生有证据的待验证假设 |
| 未授权 | 授权门在内容分析前阻断，不产出学习画像 |
| 冷启动 | 单条高置信错误只能产生 `needs_more_data`，不能成为高优先级结论 |
| 复测闭环 | 新的正确作答事件进入后，函数的 BKT 掌握度上升 |
| 完整性 | `manifest.json` 能发现产物被篡改 |
| 工具网关授权边界 | 未授权场景下，网关拒绝读取评估事件和交互观察 |
| 工具网关最小权限 | 请求元数据、角色允许列表、证据引用和先修路径在网关侧校验 |

## 已执行的真实模型预检

以下预检通过真实 DeepSeek OpenAI-compatible Chat Completions API 调用模型，不伪造模型输出，也不把
它表述为 AgentTeams Team Room 运行：

```powershell
$env:DEEPSEEK_BASE_URL = "https://api.deepseek.com"
$env:DEEPSEEK_MODEL = "deepseek-v4-flash"
$env:DEEPSEEK_API_KEY = "<local secret only>"
python agentteams\tools\live_worker_contract.py
```

本次验证中，`deepseek-v4-flash` 和 `deepseek-v4-pro` 都实际通过 DeepSeek Chat
Completions 返回了 JSON 健康合约，并都通过两条 Evidence Analyst Worker 预检：授权场景
的 `functions` 聚合为 3 条可判分事件、0 条正确、6 个 evidence refs；未授权场景返回
`BLOCKED` 且不产生概念证据或引用。脚本只从当前进程环境读取密钥，输出为脱敏摘要。

## 推荐的竞赛展示指标

| 指标 | 定义 |
| --- | --- |
| `schema_validity` | 输入和中间状态是否满足 JSON 契约 |
| `evidence_coverage_rate` | 学习假设中带有效 `evidence_refs` 的比例 |
| `unsupported_claim_rate` | 无证据结论比例，目标为 0 |
| `no_access_before_consent` | 未授权时是否在任何内容分析前阻断 |
| `plan_traceability_rate` | 每个学习路径步骤是否可回溯至概念状态或先修边 |
| `trace_completeness` | Team Leader 和每个 Worker 是否至少留下一条状态转移 |
| `artifact_integrity` | manifest 哈希校验通过率 |

## 可重复运行证据

```powershell
py run_demo.py --input examples\python_foundations.json --output runs\evidence
py -c "from cogniguide import verify_artifacts; print(verify_artifacts('runs/evidence'))"
```

`runs/` 被 `.gitignore` 排除，因为它可能含用户学习数据。演示录像或 PPT 中可以展示其完全脱敏的字段、HTML 报告和 trace 摘要。

## AgentTeams 真实运行取证清单

以下证据必须在 Docker Engine 和 AgentTeams 环境可用后采集；当前仓库不把本地 Python 运行结果误称为真实 Team 运行：

1. Manager 串行创建并健康检查 4 个业务 Worker、独立 TeamLeader 和 Team 的记录；
2. Worker 容器访问 HTTP tool gateway 的 `health` 与受控工具调用记录；
3. Team Room 向 `@cogniguide-demo-leader` 发送的两条任务及协作消息；
4. `shared/tasks/task-CG-1001/` 的结构化产物、网关 trace/audit 和最终 `HUMAN_REVIEW_REQUIRED`；
5. `CG-1002` 未授权任务的 `BLOCKED`，以及 trace 中不存在学习内容读取调用；
6. 不包含 API Key、原始学习文本或模型思维链的脱敏截图/日志摘要。
