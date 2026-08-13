---
name: interaction-evidence
description: Convert authorized, structured learning events into a traceable evidence profile without inferring correctness from free text.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Interaction Evidence

## Inputs

- Authorized assessment events: concept, scored result, pre-answer confidence, evidence ID, question type
- Optional interaction metadata for cold-start observations

## Outputs

- Per-concept evidence counts, results, confidence aggregates, question-type distribution, and `evidence_refs`

## Procedure

1. Validate the concept against the active domain pack.
2. Validate `confidence` is in `[0, 1]`.
3. Preserve the scoring provenance and evidence ID for each event.
4. Keep free-text interaction content out of the report; use it only as a non-decisive auxiliary observation.

## Failure handling and reuse

- Unknown item/concept, duplicate event, or unscored free text becomes a schema rejection or data gap.
- Reusable for employee enablement, onboarding, certification preparation, and knowledge-base training.
