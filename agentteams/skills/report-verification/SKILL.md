---
name: report-verification
description: Independently verify evidence coverage, privacy constraints, prerequisite validity, and human-review gates before publishing a CogniGuide report.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Report Verification

## Inputs

- Policy, interaction profile, learner state, and learning plan artifacts

## Outputs

- Publish/return-for-revision/human-review decision, verified report, and audit event

## Quality gates

1. Every hypothesis must resolve all `evidence_refs`.
2. Every path step must link to a concept state or a declared prerequisite edge.
3. No report may contain raw conversation text, clinical language, or unapproved persistent profiling.
4. Low evidence, privacy findings, or calibration instability must be visible to the user.
5. At most one controlled revision is allowed; then require human review.

## Reuse value

The Skill is domain-independent: it can verify any multi-Agent report that relies on evidence, a policy gate, and a structured plan.
