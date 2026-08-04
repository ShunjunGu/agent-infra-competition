---
name: knowledge-tracing
description: Estimate transparent per-concept learning state using evidence-backed BKT and confidence calibration.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Knowledge Tracing

## Inputs

- Ordered, scored assessment events with concept and confidence
- Versioned BKT parameters and mastery thresholds

## Outputs

- BKT mastery estimate, calibration error/Bias/Brier score, evidence-backed hypotheses, human-review decision

## Procedure

1. Update each concept with declared BKT parameters; record parameter version.
2. Calculate confidence-versus-outcome measures only from scored events.
3. Mark high-confidence errors as observations, not psychological diagnoses.
4. If fewer than 3 scored events exist for a concept, return `needs_more_data`.

## Failure and safety boundary

- Missing parameter version or invalid scores stops the estimation.
- Do not claim educational effectiveness or stable learner traits from a short sequence.
- A production implementation must calibrate parameters on held-out, consented data.
