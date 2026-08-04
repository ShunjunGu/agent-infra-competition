# CogniGuide AgentTeams 适配层

## 重要边界

`../cogniguide/` 已提供无需 API Key 的本地参考运行时并有自动测试。本目录是将同一工作流接入 **AgentTeams** 的声明式设计材料和 Manager 创建模板；仓库目前没有把本目录当作“已部署 AgentTeams”的运行证据。

这样设计有两个目的：

1. 评委/协作者可立即运行确定性 Demo，复现业务闭环；
2. 有 AgentTeams 环境、LLM 凭据和工具网关后，可按同一角色、Skill 和共享状态契约部署真实 Team，而无需重新发明业务逻辑。

## Team 拓扑

```text
Manager（只负责创建、健康检查和权限）
  └─ cogniguide-demo-leader（独立 TeamLeader）
       ├─ interaction-evidence-analyst
       ├─ knowledge-state-estimator
       ├─ learning-path-planner
       └─ report-verifier
```

Manager 不进入业务 Team Room；TeamLeader 是独立 Worker，不复用业务 Worker。该形态与仓库中的官方 OpsPilot 基线一致。

## 结构化共享状态

Worker 之间必须传递 JSON 产物，不把自然语言摘要当作唯一事实源。完整样例见 [`task_state.example.json`](task_state.example.json)。

| 状态 | 产生者 | 下游使用者 | 关键字段 |
| --- | --- | --- | --- |
| `policy` | Consent Boundary | 全部 Worker | `analysis_authorized`、`human_review_required` |
| `interaction_profile` | Evidence Analyst | Knowledge State | `evidence_refs`、结果、confidence |
| `knowledge_state` | State Estimator | Planner、Verifier | BKT 状态、校准、待验证假设 |
| `learning_plan` | Planner | Verifier、TeamLeader | 先修关系、验收条件、复测安排 |
| `report` | Verifier | TeamLeader | 可发布结论、限制、人工复核 |

建议在 AgentTeams 共享任务目录（例如 `shared/tasks/task-<id>/`）或等价对象存储中持久化这些版本化 JSON；每一次写入附带 `task_id`、`schema_version`、`trace_id` 和 SHA-256。

## 部署步骤

1. 按官方 AgentTeams 文档在隔离环境完成安装、模型配置和认证；不要提交 API Key、Manager 密码或真实学习数据；
2. 将可被 Worker 容器访问的工具网关配置为本地/受控地址；
3. 阅读 [`team_spec.json`](team_spec.json) 和 [`create_agents_messages.md`](create_agents_messages.md)；
4. 在 Manager 房间**串行**创建 4 个业务 Worker，逐个健康检查后创建 Team 与独立 TeamLeader；
5. 在 Team Room 由用户 `@cogniguide-demo-leader` 提交一条授权分析任务；
6. 保存每个状态产物、工具结果摘要和最终报告，运行 manifest 校验；
7. 分别演示完整主路径、低样本、未授权三条路径。

## 工具/MCP 契约

生产接入可将以下契约实现为 MCP Server、HTTP 网关或企业内部服务；业务 Skill 不应绑定具体部署实现。

| 工具 | 仅允许角色 | 作用 | 失败处理 |
| --- | --- | --- | --- |
| `assessment.validate` | Evidence Analyst | 对照版本化题库/Rubric 输出可判分事件 | 未知题目拒绝，不猜测正确性 |
| `framework.retrieve` | State Estimator、Planner | 查询版本化概念 DAG/学习资源 | 无匹配时走通用框架并标记限制 |
| `evidence.verify` | Report Verifier | 检查所有引用是否存在 | 缺引用则拒绝发布 |
| `plan.validate` | Report Verifier | 检查路径未跨越先修/无自动执行动作 | 不通过则退回一次 |
| `audit.append` | TeamLeader、Verifier | 追加最小化审计事件 | 失败时将任务置为待人工复核 |

所有工具调用必须包含 `task_id`、`trace_id`、`actor` 和 `schema_version`；原始对话文本不应写入审计日志。

## 安全与审批

- 未授权：在任何读取/分析学习内容前阻断；
- 低样本：不输出高优先级个体结论，仅请求补充测验；
- 个人信息：报告中脱敏，默认要求人工复核；
- 长期画像：只有用户确认后才允许写入，未确认数据仅用于当前任务；
- 自动动作：本项目只有学习建议，没有代替用户报名、发送、修改或做高风险决定的权限；
- 返工：Verifier 最多允许一个受控的 `REVISE_ONCE`，防止无限 Agent 互评。
