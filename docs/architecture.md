# CogniGuide 架构与安全边界

## 1. 设计目标

CogniGuide 的目标不是用大模型给学习者贴“认知盲区”标签，而是构建一个可复用的学习分析工作流：每条建议都可回溯到**可判分学习事件、模型状态、先修关系、路径决策和验证规则**。

这使它可以服务企业培训、岗位能力提升和知识工作流，而非只是一轮个人聊天。

## 2. 双运行层

| 层 | 当前状态 | 责任 |
| --- | --- | --- |
| `cogniguide/` 本地参考运行时 | 已测试 | 无 API Key 的确定性闭环、产物和回归测试 |
| `agentteams/` 适配层 | 设计/待环境验证 | 在 AgentTeams 中创建独立 TeamLeader、Worker、Skill、共享状态和审批策略 |

两层共享同一份业务角色、输入输出契约和安全策略。参考运行时不伪装为 AgentTeams 运行证据。

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

Team Leader 只负责路由和状态转换；业务结论由 Worker 的结构化产物输出；Verifier 不允许无证据结论发布。

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

## 7. 竞赛价值

本设计把“多 Agent 协同”落到可审计系统能力：角色隔离、结构化上下文、可替换 Skill、验证门、异常分支、完整性证明和人工确认，而不是把多个 Prompt 串起来。
