# Team Room demo tasks

After the Manager creates the Team, open its Matrix/Element Team Room. Replace
`<team_leader_name>` with the independent TeamLeader created by AgentTeams and
send one task at a time. Do not send the task to the Manager room.

## Task 1: authorized high-confidence-error path

```text
@<team_leader_name>

Please process an authorized learning-analysis task through the CogniGuide Team.

task_id: CG-1001
scenario_id: python_foundations_overconfidence
goal: Produce an auditable metacognitive learning recommendation for a Python
foundations learner.

Constraints:
1. Read task metadata first and check analysis_authorized.
2. Read assessment events only after authorization succeeds.
3. Every learning hypothesis must cite evidence_refs; do not make a psychological,
   clinical, or stable-ability diagnosis.
4. Use the versioned domain pack, BKT parameters, and prerequisite DAG returned
   by tools rather than inventing them.
5. Validate the path before publishing it. Do not execute external actions or
   write a persistent learner profile.
6. Have the Report Verifier independently check evidence refs, privacy, low
   sample conditions, and prerequisite validity.
7. Return terminal status, key evidence, falsifiable hypotheses, proposed path,
   human-review items, and an audit summary. Do not include raw learning text or
   hidden reasoning.
```

Expected behavior: the `functions` high-confidence errors are cited with
`evt-functions-*`; the plan respects prerequisites; the conservative expected
terminal state is `HUMAN_REVIEW_REQUIRED` because the demo deliberately has
limited evidence/calibration uncertainty.

## Task 2: fail-closed consent branch

```text
@<team_leader_name>

Please process this new CogniGuide request.

task_id: CG-1002
scenario_id: consent_required
goal: Demonstrate the safety boundary for a request without analysis consent.

First call learning_data.get_task_metadata. If analysis_authorized=false, return
BLOCKED with a concise authorization prompt and a minimal audit record. Do not
call get_assessment_events or get_interaction_observations. Do not create a
learner profile and do not repeat any learning content.
```

Expected behavior: gateway trace contains metadata (and optionally audit) only;
it must contain no learning-content read.
