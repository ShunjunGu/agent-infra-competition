# CogniGuide HTTP gateway to MCP mapping

The local HTTP gateway exists so AgentTeams Workers can call concrete tools in a
runnable demo. It only reads scenario data, validates references/paths, and
appends minimized audit events. It does **not** route agents, select roles, or
perform orchestration; those are AgentTeams Manager and TeamLeader responsibilities.

For production, expose the same capability boundaries as an MCP server. Keep the
Worker-facing contract stable while replacing mock data sources with approved
learning systems.

## Mapping

| Capability | Demo HTTP call | Intended MCP tool | Allowed roles | Boundary |
| --- | --- | --- | --- | --- |
| Read task consent/metadata | `POST /tools/{scenario}/learning_data.get_task_metadata` | `learning.get_task_metadata` | TeamLeader, all Workers | metadata first; no content returned |
| Read scored assessment events | `POST /tools/{scenario}/learning_data.get_assessment_events` | `learning.get_assessment_events` | Evidence Analyst | gateway denies it without authorization |
| Read non-decisive interaction observations | `POST /tools/{scenario}/learning_data.get_interaction_observations` | `learning.get_interaction_observations` | Evidence Analyst | authorized only; raw text excluded from reports |
| Read domain DAG/resources | `POST /tools/{scenario}/framework.get_domain_pack` | `framework.get_domain_pack` | State Estimator, Path Planner | versioned pack only |
| Read BKT parameters | `POST /tools/{scenario}/framework.get_bkt_parameters` | `framework.get_bkt_parameters` | State Estimator | registered parameter version required |
| Verify evidence IDs | `POST /tools/{scenario}/evidence.verify_refs` | `evidence.verify_refs` | Report Verifier | no inference from unresolved refs |
| Validate prerequisite path | `POST /tools/{scenario}/plan.validate_prerequisites` | `learning_path.validate_prerequisites` | Path Planner, Report Verifier | rejects unknown concepts, bad order, external actions |
| Append minimized audit record | `POST /tools/{scenario}/audit.append` | `audit.append` | TeamLeader, all Workers | rejects missing provenance; strips raw text/CoT/keys |

`{scenario}` is a demo-only fixture selector. A production MCP server should use
an opaque, authorization-scoped task handle instead of a filename-like scenario
identifier.

## HTTP contract

All tool calls use JSON:

```http
POST <MOCK_TOOL_BASE_URL>/tools/python_foundations_overconfidence/evidence.verify_refs
Content-Type: application/json

{
  "schema_version": "cogniguide.tool-request/v1",
  "task_id": "CG-1001",
  "trace_id": "cg1001-verifier-001",
  "actor": "report-verifier",
  "evidence_refs": ["evt-functions-01", "evt-functions-02"]
}
```

The response envelope is:

```json
{
  "ok": true,
  "result": {
    "valid": true,
    "requested_count": 2,
    "resolved_count": 2,
    "missing_refs": []
  }
}
```

The matching MCP tool should expose a structured input schema with the same
business fields and return the `result` object, not an HTTP envelope.

## Required provenance and data handling

Every HTTP tool request must carry the versioned envelope
`schema_version=cogniguide.tool-request/v1`, `task_id`, `trace_id`, and `actor`.
The gateway validates task scope and the demo role allow-list before invoking a
tool. Each Worker-written artifact and audit event must also carry
`schema_version`, `task_id`, `trace_id`, `actor`/`producer`, and `evidence_refs`
where applicable. The current audit endpoint requires an event whose provenance
fields exactly match its request envelope:

```json
{
  "task_id": "CG-1001",
  "trace_id": "trace-...",
  "actor": "report-verifier",
  "event": "verification_complete",
  "status": "human_review_required"
}
```

MCP implementations must preserve the same fail-closed authorization rule and
must not persist raw conversation text, model reasoning, API keys, or durable
learner profiles without separate explicit approval.

## Migration checklist

1. Implement the eight MCP tools with the schemas above.
2. Bind caller identity and task scope server-side; do not trust user-provided
   role strings alone.
3. Replace scenario fixtures with consented, versioned data sources.
4. Keep audit logs hash-based and data-minimized.
5. Run the two demo scenarios unchanged against the MCP adapter before changing
   Team prompts or Worker contracts.
