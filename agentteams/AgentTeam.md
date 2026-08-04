# CogniGuide AgentTeams Native Team

`agentteams/` is the primary runnable integration for this competition entry. It
uses AgentTeams for Worker lifecycle, TeamLeader routing, collaboration, and
shared task state. `tools/` is deliberately only an HTTP data/validation gateway;
it must not be treated as an agent orchestrator or a replacement workflow engine.

## Topology

```text
AgentTeams Manager
  -> Team: cogniguide-demo
       -> independent TeamLeader: cogniguide-demo-leader
            -> interaction-evidence-analyst
            -> knowledge-state-estimator
            -> learning-path-planner
            -> report-verifier
            -> HTTP tool gateway (data, validation, audit only)
```

The Manager creates and health-checks Workers serially, then creates the Team
and a **new, independent** TeamLeader. The Manager does not enter the Team Room
and does not perform learning analysis. The TeamLeader coordinates artifacts; it
does not rewrite Worker evidence or infer facts without a cited artifact.

## Team-level rules

1. A task begins only when a user mentions `@cogniguide-demo-leader` in the Team
   Room and supplies `task_id` and `scenario_id`.
2. The evidence analyst reads task metadata before any learning-content tool.
   `analysis_authorized=false` is fail-closed: output `BLOCKED`, add a minimal
   audit event, and do not dispatch downstream analysis.
3. Workers exchange versioned JSON artifacts in
   `shared/tasks/task-{task_id}/`; free-form summaries are not a source of truth.
4. Every claim about learning evidence has resolvable `evidence_refs`. No Worker
   stores raw conversation text, chain-of-thought, API keys, or durable learner
   profiles.
5. Every gateway request carries `schema_version=cogniguide.tool-request/v1`,
   `task_id`, `trace_id`, and the calling Worker `actor`; the gateway rejects
   mismatched task scope, unauthorized roles, and learning-content reads without
   consent.
6. The verifier independently checks evidence references, prerequisite order,
   privacy boundaries, and low-sample conditions. It may request one controlled
   revision; a second failure becomes `HUMAN_REVIEW_REQUIRED`.

## Artifact protocol

Each artifact includes at least:

```json
{
  "schema_version": "0.1.0",
  "task_id": "CG-1001",
  "trace_id": "trace-...",
  "producer": "worker-name",
  "evidence_refs": []
}
```

| Artifact | Producer | Required decision content |
| --- | --- | --- |
| `01_interaction_profile.json` | Interaction Evidence Analyst | consent result, per-concept scored evidence, data gaps |
| `02_learner_state.json` | Knowledge State Estimator | parameter version, BKT state, calibration, falsifiable hypotheses |
| `03_learning_path.json` | Learning Path Planner | prerequisite-aware phases, acceptance criteria, validation result |
| `04_report_verification.json` | Report Verifier | final status, evidence/path checks, human-review reasons |

Allowed terminal statuses are `PUBLISHED`, `NEEDS_MORE_DATA`,
`HUMAN_REVIEW_REQUIRED`, and `BLOCKED`.

## Native execution boundary

The HTTP gateway can be unit-tested without Docker, but that proves only tool
contracts. A live AgentTeams demonstration requires Docker, a configured
AgentTeams/Matrix environment, four healthy Workers, an independent TeamLeader,
and visible Team Room collaboration. Follow
[`AGENTTEAMS_RUNBOOK.md`](AGENTTEAMS_RUNBOOK.md) for that validation.

## Root entrypoints

- [`AGENTTEAMS_RUNBOOK.md`](AGENTTEAMS_RUNBOOK.md): environment setup and
  validation evidence.
- [`create_agents_messages.md`](create_agents_messages.md): one Manager message
  that creates the native Team.
- [`run_demo_task_message.md`](run_demo_task_message.md): Team Room tasks.
- [`MCP_MAPPING.md`](MCP_MAPPING.md): HTTP gateway to MCP production mapping.
- [`agents/`](agents/): Worker contracts.
