# Phase 162: Task Broker Model-Tier Routing Policy

Status: completed

## Goal

Add a deterministic routing policy that lets the task broker choose cheaper
worker/model tiers for easy, low-risk tasks while escalating uncertain, failing,
or policy-sensitive tasks to stronger workers.

## Primary ROI

Cost high, quality medium-high, speed high: model-tier routing should reduce
routine task cost without letting cheap workers silently degrade verification,
handoff quality, or merge safety.

## Scope

- Define `ModelRoutingPolicy` or equivalent task-broker routing contract.
- Use existing task evidence where available:
  - task goal and constraints;
  - allowed and forbidden paths;
  - lock scope;
  - file/package risk;
  - required verification commands;
  - recent failure/repair facts;
  - estimated context size;
  - task difficulty/confidence scores from Phase 159.
- Classify routes such as:
  - cheap/local worker allowed;
  - standard worker required;
  - strong worker required;
  - human review required before dispatch.
- Require escalation on:
  - failed verification;
  - low routing confidence;
  - security, release, credential, CI, architecture, or public API surfaces;
  - repeated cheap-worker failure;
  - oversized context or ambiguous ownership.
- Emit compact routing explanations into task handoffs and runtime events.
- Keep routing advisory until dogfood data proves low false-negative risk.

## Non-Goals

- Do not choose or integrate a specific model provider in this phase.
- Do not add OpenAI Agents SDK, Claude, Codex, OpenHands, LangGraph, AutoGen, or
  CrewAI worker implementations.
- Do not let worker backends decide their own risk policy.
- Do not route production credentials, secrets, or sensitive data to cheaper
  workers.
- Do not make cheap-worker routing blocking or automatic until measured data is
  available.

## Verification Acceptance Criteria

- Unit tests cover low-risk routing, high-risk escalation, low-confidence
  escalation, repeated-failure escalation, and verification-failure escalation.
- Handoff output includes the selected tier and a compact reason.
- Runtime events record route decisions without leaking sensitive context.
- Router policy does not import model-provider SDKs.
- Task-broker downstream install contract still passes.
- `python3 -m agent_maintainer verify --profile fast`
- `tach check --exact`

## Notes For Future Tasks

This phase is where "spawn a less expensive model for easier tasks" becomes a
testable product behavior. Keep it deterministic first. DSPy, LLM judges, or
learned routing may improve it later, but only after the scoring dataset and
dogfood runs produce enough labeled examples.
