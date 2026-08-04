# 研究依据与可落地方法

本 Demo 借鉴以下顶会/顶刊方法的**可验证部分**。它不宣称复现原论文，也不把小样本 Demo 包装为经教育实验验证的产品效果。

## 1. Bayesian Knowledge Tracing（BKT）

- 依据：Corbett & Anderson, *Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge*, **User Modeling and User-Adapted Interaction**, 1995. [DOI](https://doi.org/10.1007/BF01099821)
- Demo 落点：每个知识点按事件顺序以固定 `prior=0.2`、`learn=0.15`、`guess=0.2`、`slip=0.1` 更新掌握概率。
- 约束：这些是演示参数；真实部署必须依据历史数据和保留集校准，不能把 `p_mastery` 解释为人的真实能力测量。

对一次作答观测，令当前掌握概率为 `p`：

```text
P(correct) = p * (1 - slip) + (1 - p) * guess

答对：p_observed = p * (1 - slip) / P(correct)
答错：p_observed = p * slip / (1 - P(correct))

p_next = p_observed + (1 - p_observed) * learn
```

## 2. 元认知校准

- 依据：Koriat, *Monitoring One’s Own Knowledge During Study*, **Journal of Experimental Psychology: General**, 1997. [DOI](https://doi.org/10.1037/0096-3445.126.4.349)；Gutierrez de Blume et al., *Calibrating Calibration*, **Journal of Educational Psychology**, 2022. [DOI](https://doi.org/10.1037/edu0000674)
- Demo 落点：记录答前 `confidence` 和可观察结果，输出校准误差、Bias、Brier 分数和高置信错误信号。
- 安全边界：少于 3 条同概念可判分证据时只标记 `needs_more_data`；少量事件不得推出稳定的总体认知结论，更不能声称“达克效应”。

```text
calibration_error = mean(abs(confidence_i - outcome_i))
bias              = mean(confidence_i - outcome_i)
brier_score       = mean((confidence_i - outcome_i)^2)
```

## 3. 先修知识图谱

- 依据：Pan et al., *Prerequisite Relation Learning for Concepts in MOOCs*, **ACL 2017**. [ACL Anthology](https://aclanthology.org/P17-1133/)
- Demo 落点：首版维护小型、可人工审计的领域 DAG；Planner 递归补齐前置概念并按拓扑顺序安排活动。
- 安全边界：不让 LLM 自动制造图边；生产中每条边应有来源、版本、审核人和回滚机制。

## 4. 自我调节学习（SRL）与可执行干预

- 依据：Zimmerman, *Becoming a Self-Regulated Learner*, **Theory Into Practice**, 2002. [DOI](https://doi.org/10.1207/s15430421tip4102_2)
- 落点：系统显式支持“计划 → 监控 → 反思 → 复测 → 重规划”，而非输出一次性 To-do List。
- 练习策略依据：Dunlosky et al., *Improving Students’ Learning With Effective Learning Techniques*, **Psychological Science in the Public Interest**, 2013. [DOI](https://doi.org/10.1177/1529100612453266)。Demo 将其转化为可判分检索练习和迁移任务，而不是泛泛推荐“多看资料”。

## 5. Agent 工程：证据、验证和受控反思

| 研究 | 可借鉴点 | Demo 中的约束 |
| --- | --- | --- |
| [ReAct, ICLR 2023](https://openreview.net/forum?id=WE_vluYUL-X) | 推理和观察/工具结果交替 | 先有评估证据和框架状态，再生成学习假设 |
| [CRITIC, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/fef126561bbf9d4467dbb8d27334b8fe-Abstract-Conference.html) | 外部工具反馈驱动验证 | Verifier 检查证据、Schema、权限和低样本约束 |
| [Self-RAG, ICLR 2024](https://research.ibm.com/publications/self-rag-learning-to-retrieve-generate-and-critique-through-self-reflection) | 检索和批判要有相关性/支撑性门 | 后续 RAG 仅在证据不足/框架不匹配时调用，并保留引用 |
| [Reflexion, NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html) | 基于任务反馈的有限反思 | 验证失败后最多一次返工；反思记录是工作流证据，不是用户画像 |
| [AgentBench, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/e9df36b21ff4ee211a8b71ee8b7e9f57-Abstract-Conference.html) | Agent 应被当作多轮执行系统评测 | 用 fixture、终态、约束满足和审计完整性测试，而不是只看报告文案 |

## 6. 后续扩展边界

- **题库/Rubric 工具**：由工具输出可追溯评分，不让 LLM 直接判对错；
- **RAG**：认知框架、岗位能力模型、课程资源均需版本与引用；
- **用户确认驱动长期记忆**：只有用户确认后才写入长期学习画像，未确认的本次分析只保留临时状态；
- **真实数据后再探索 DKT/NeuralCD**：例如 [Deep Knowledge Tracing, NeurIPS 2015](https://proceedings.neurips.cc/paper_files/paper/2015/hash/bac9162b47c56fc8a4d2a519803d51b3-Abstract.html)，但必须有足够训练、验证和泛化评测数据。
