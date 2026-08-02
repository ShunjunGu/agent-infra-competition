# 🧠 认知向导 CogniGuide — AI 元认知学习助手

> **别家 AI 教你学内容，CogniGuide 教你看见自己怎么思考。**

「讯飞 Agent Infra 比赛」参赛作品 · Datawhale AI 学习中心赛道

---

## 📌 项目是什么

CogniGuide 是一个基于 **AgentTeams 多 Agent 协作** 的 AI 元认知学习助手。

它分析**你与 AI 助手的交互记录**（把它当作"思维日志"），通过多个专业 Agent 协同工作，识别你的：
- 🧩 **思维盲区** —— 该知道但没问过、总绕开的知识领域
- 🔍 **认知偏差** —— 反复追问同类问题、从不质疑前提假设等模式
- 🛤️ **学习路径** —— 针对盲区生成的分阶段、个性化学习计划

**一句话价值**：多数学习工具告诉你"学什么"，CogniGuide 告诉你"**你为什么没学会**"。

## 🔄 为什么选这个方向

- **独创性**：市面 AI 学习产品扎堆"内容推荐"，几乎没有产品做"思维模式分析"（元认知层）
- **数据源独特**：AI 对话即思维日志——越来越多人的思考过程体现在与 AI 的对话里
- **真实问题**：达克效应（"不知道自己不知道"）是学习低效的根本原因之一

## 🤖 多 Agent 分工

| Agent | 职责 | 核心 Skill |
|---|---|---|
| **交互分析师** | 解析对话数据，提取提问模式 / 主题分布 | 交互模式解析 |
| **盲区识别师** | 对照认知框架库，定位思维盲区 | 认知框架库 + 盲区定位 |
| **路径规划师** | 将盲区转化为分阶段学习路径 | 学习路径生成 |
| **洞察生成员** | 输出元认知洞察报告 + 资源推荐 | 洞察报告生成 |

协作流水线：`AI交互数据 → 交互分析师 → 盲区识别师 → 路径规划师 → 洞察生成员 → 报告`

## 📂 仓库内容

```
├── 方案材料.md              # 作品简介 + 方案 PPT 内容框架（核心文档）
├── url-to-markdown/         # Datawhale Baseline 教程抓取资料
└── opspilot-zero-demo.zip   # 官方赛题 Demo（AgentTeams 多 Agent 事故处理）
```

> 🔒 `AgentTeams-配置信息.md`（含环境凭据）已在 `.gitignore` 中排除，**不会进入仓库**。

## 🚀 如何参与协作

```bash
# 1. 克隆仓库
git clone https://github.com/ShunjunGu/agent-infra-competition.git
cd agent-infra-competition

# 2. 每次开始前拉最新
git pull

# 3. 创建自己的分支（建议）
git checkout -b your-name/feature

# 4. 提交改动
git add <文件>
git commit -m "描述你的改动"

# 5. 推送分支并开 PR（或直接推到 main，需大家约定）
git push origin your-name/feature
```

**协作约定建议**：
- 分支命名：`姓名/功能`，如 `xiaoming/ppt`、`xiaohong/demo`
- 修改文档后及时 `git pull` 避免冲突
- 需要评审的改动走 Pull Request

## 📋 当前进度

| 阶段 | 状态 |
|---|---|
| AgentTeams Baseline 跑通（OpsPilot Demo） | ✅ |
| 选题方向确定（AI 元认知学习助手） | ✅ |
| 作品简介 + 方案 PPT 框架 | ✅ |
| PPT 模板填充 | 🔄 进行中 |
| 可运行 Demo | ⏳ 待做 |
| 赛事提交 | ⏳ 待做 |

## 👥 团队成员

- 待补充（姓名 / 学校 / 分工）

---

*讯飞 Agent Infra 比赛 · AgentTeams 多 Agent 协同作品*
