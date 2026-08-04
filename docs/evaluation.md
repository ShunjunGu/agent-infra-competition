# 评测与运行证据

## 已自动化验证

```powershell
py -m unittest discover -s tests -v
```

| 用例 | 验证目标 |
| --- | --- |
| 完整主路径 | Team Leader 与 4 个角色按顺序留下结构化 trace，函数概念产生有证据的待验证假设 |
| 未授权 | 授权门在内容分析前阻断，不产出学习画像 |
| 冷启动 | 单条高置信错误只能产生 `needs_more_data`，不能成为高优先级结论 |
| 复测闭环 | 新的正确作答事件进入后，函数的 BKT 掌握度上升 |
| 完整性 | `manifest.json` 能发现产物被篡改 |

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
