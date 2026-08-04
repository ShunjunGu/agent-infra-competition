# CogniGuide：证据驱动的元认知学习协同系统

> 不让 Agent 凭对话“猜”学习者的盲区；让每一条学习建议都能回溯到可判分证据、掌握度模型、置信度校准和先修关系。

CogniGuide 是面向学习运营、企业培训和知识工作者能力发展的多 Agent 协同 Demo。它把“学习证据 → 知识状态 → 先修路径 → 复测与反思”做成一个可复现、可审计、可安全降级的闭环。

本仓库包含两层交付：

1. **本地参考运行时**：纯 Python 标准库、无需 API Key，一键运行并生成 HTML/Markdown/JSONL 证据；
2. **AgentTeams 接入契约**：将本地角色、Skills、共享状态和安全策略映射为 AgentTeams Team 的可审查配置材料。

> 本地参考运行时是当前已验证的可运行 Demo；`agentteams/` 是接入设计与 Manager 创建模板，**不宣称已经在本机启动了 AgentTeams**。

## 30 秒运行

环境：Python 3.11+；没有第三方依赖。

```powershell
cd D:\AIcompetation\agent-infra-competition
py run_demo.py --input examples\python_foundations.json --output runs\python-foundations
Start-Process runs\python-foundations\report.html
```

Windows 下也可双击：

```text
run_demo.bat
```

启动本地交互界面：

```powershell
py run_demo.py --serve
# 浏览器打开 http://127.0.0.1:8080
```

运行“初测 → 路径 → 复测 → 重规划”闭环演示：

```powershell
py run_closed_loop_demo.py --output runs\closed-loop
Start-Process runs\closed-loop\round-2\report.html
```

运行测试：

```powershell
py -m unittest discover -s tests -v
```

## Demo 证明什么

```text
已授权的结构化评估事件
  → Interaction Evidence Analyst：整理概念、结果、信心和证据 ID
  → Knowledge State Estimator：BKT 掌握度 + 校准误差/Brier 分数
  → Learning Path Planner：先修 DAG 约束下生成练习与复测路径
  → Report Verifier：检查证据、低样本、隐私和人工复核条件
  → 审计产物：状态 JSON、JSONL trace、报告、SHA-256 manifest
```

| 角色 | 主要 Skill | 输出契约 |
| --- | --- | --- |
| Team Leader | 状态编排、一次性调度 | 任务状态、审计轨迹、最终汇总 |
| Interaction Evidence Analyst | `interaction-evidence` | 概念证据画像、题型分布、证据引用 |
| Knowledge State Estimator | `knowledge-tracing` | BKT 掌握度、置信度校准、待验证假设 |
| Learning Path Planner | `prerequisite-path` | 有先修约束的阶段计划、验收标准 |
| Report Verifier | `report-verification` | 证据覆盖、安全边界、人工复核结论 |

所有结论都标注为“待验证学习假设”，而不是对学习者进行人格、心理或能力诊断。

## 关键工程能力

- **授权优先**：`consent.analysis_authorized=false` 时在内容分析前阻断；
- **低样本降级**：少于 3 条可判分证据的概念只能标为 `needs_more_data`，不会产生高优先级“盲区”判断；
- **证据化建模**：主输入是可判分学习事件和答前信心，原始对话只做辅助观察，不直接决定掌握度；
- **先修图谱**：路径先补前置依赖，再处理高风险目标；
- **可观测**：每个 Agent 状态转移写入 `trace.jsonl`，仅记录结构化动作、哈希和证据 ID，不记录思维链；
- **完整性**：`manifest.json` 对所有产物做 SHA-256 校验；测试覆盖篡改检测；
- **闭环重规划**：`run_closed_loop_demo.py` 导入复测证据后重新估计掌握度和学习路径。

## 输出产物

每次命令行运行写入 `runs/<name>/`（已忽略，不会提交可能含学习数据的产物）：

```text
input_sanitized.json             # 无原始文本的输入摘要
01_interaction_profile.json      # 证据画像
02_learner_state.json            # BKT/校准/待验证假设
03_learning_path.json            # 先修约束的学习路径
04_report_verification.json      # 报告质量与安全边界
trace.jsonl                      # Agent 状态转移与哈希审计
report.md / report.html          # 人类可读报告
manifest.json                    # 产物完整性校验
result.json                      # 组合结果
```

## 研究方法与比赛映射

实现没有把顶会/顶刊方法当成营销词，而是保留了可验证的落点：

- BKT：可解释地更新知识点掌握度；
- 元认知校准：使用 confidence、校准误差和 Brier 分数定位“高置信错误”事件；
- 先修关系 DAG：禁止路径静默跳过未掌握前置知识；
- SRL（计划—监控—反思—再计划）：通过复测输入触发重新规划；
- 验证型 Agent 工作流：Verifier 独立检查证据引用、隐私与低样本约束。

详见 [`docs/research-basis.md`](docs/research-basis.md)、[`docs/architecture.md`](docs/architecture.md) 和 [`docs/evaluation.md`](docs/evaluation.md)。

## AgentTeams 映射

竞赛要求以 AgentTeams 作为多 Agent 协同设计基点。仓库中的 [`agentteams/`](agentteams/) 保留了：

- 独立 TeamLeader + 4 个业务 Worker 的同构 Team Spec；
- 可复制给 Manager 的创建请求模板；
- Skills 的输入、输出、失败处理与安全边界；
- 共享状态、权限、审批与审计的部署映射。

见 [`agentteams/README.md`](agentteams/README.md)。参考运行时和 AgentTeams 的边界在文档中明确区分，避免把离线脚本误表述为生产 Team。

## 当前阶段

| 项目项 | 状态 |
| --- | --- |
| 选题与初赛作品简介 | 已完成，见 `方案材料.md` |
| 无 API Key 本地可运行 Demo | 已完成 |
| 多 Agent 结构化状态、审计、低样本/授权分支 | 已完成 |
| AgentTeams 接入契约与创建模板 | 已完成（待真实环境验证） |
| 正式 AgentTeams 运行证据 / Demo 视频 | 待做 |
| 初赛 PPT/PDF 与团队介绍 | 待做 |

## 仓库结构

```text
cogniguide/                 # 参考运行时、编排与本地 Web API
examples/                    # happy path、冷启动、未授权、复测样例
agentteams/                  # AgentTeams Team/Skill/共享状态映射
docs/                        # 架构、研究依据、评测方法
tests/                       # 无第三方依赖的回归测试
web/                         # 本地浏览器演示 UI
run_demo.py                  # CLI / Web 服务入口
run_closed_loop_demo.py      # 初测与复测闭环演示
```

## 协作约定

```powershell
git pull --ff-only
git switch -c your-name/feature
py -m unittest discover -s tests -v
git add <明确文件>
git commit -m "描述改动"
git push -u origin your-name/feature
```

敏感配置、学习者原始数据和 `runs/` 产物禁止提交。对模型参数、知识图谱边和题库规则的改动需要附带可复现样例或测试。
