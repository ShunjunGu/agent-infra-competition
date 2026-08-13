---
name: consent-boundary
description: Enforce explicit authorization, data minimization, and human review before CogniGuide analyzes learning evidence.
metadata:
  version: "0.1.0"
  maturity: demo
---

# Consent Boundary

## Purpose

Run before every content or assessment operation. It decides whether the task can proceed and records only a minimal audit result.

## Inputs

- `consent.analysis_authorized: boolean`
- retention preference and optional privacy scan summary

## Outputs

- `policy.decision`: `allow` or `block`
- `policy.human_review_required`
- reason code without raw learning text

## Procedure

1. Require an explicit Boolean authorization.
2. If false, emit `BLOCKED`; do not call content, retrieval, or scoring tools.
3. If true, allow only the minimal data needed for this task.
4. Flag detected personal-information patterns for human review; do not reproduce them in reports.

## Failure and security boundary

- Missing or ambiguous authorization is a fail-closed condition.
- This Skill never grants persistent-profile permission by inference.
- Audit records contain hashes and result codes, never chain-of-thought or raw conversation content.
