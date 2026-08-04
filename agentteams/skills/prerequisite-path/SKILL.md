---
name: prerequisite-path
description: Produce prerequisite-aware, evidence-traceable learning actions and reassessment plans.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Prerequisite Path

## Inputs

- Knowledge-state artifact
- Versioned concept DAG and available exercise catalog

## Outputs

- Ordered phases, concept-level activities, acceptance criteria, evidence to collect, and reassessment schedule

## Procedure

1. Validate the DAG is acyclic and all nodes resolve.
2. Collect prerequisite closure for selected target concepts.
3. Order concepts topologically, then attach retrieval practice, self-explanation, and reassessment evidence requirements.
4. Allow the user to override or defer a suggested path; do not lock progression.

## Failure and reuse

- Missing/cyclic graph stops planning rather than inventing edges.
- Reusable for learning plans, compliance training, skills matrices, and certification preparation.
