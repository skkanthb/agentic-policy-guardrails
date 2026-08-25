# agentic-policy-guardrails

# Agentic Policy Guardrails: Deterministic Control Planes for Autonomous LLM Agents

## Overview
As autonomous AI agents shift from passive text generation to transactional execution (calling APIs, executing SQL queries, and interacting via protocols like Model Context Protocol / MCP), non-deterministic LLM behavior introduces severe enterprise security risks. 

This repository provides an architectural blueprint and reference Policy-as-Code implementation using **Open Policy Agent (OPA/Rego)** to intercept and evaluate agent tool calls on the wire—enforcing deterministic enterprise security boundaries before database or API execution.

## Threat Model & Failure Modes Addressed
1. **Unsanitized Payload Mutation:** AI agents passing out-of-bounds numerical arguments (e.g., credit overrides exceeding managerial thresholds).
2. **System Prompt Injection / Drift:** Malicious context manipulation forcing agents to invoke unprivileged tools.
3. **Privilege Escalation:** Agent execution attempting high-risk operations without mandatory Human-in-the-Loop (HITL) tokens.

## System Architecture
+-----------------------------------------------------------+
|                    Autonomous AI Agent                    |
+-----------------------------------------------------------+
                              |
                              | (JSON-RPC Tool Call Payload)
                              v
+-----------------------------------------------------------+
|                 L7 Interception Proxy                     |
|  +-----------------------------------------------------+  |
|  |           Open Policy Agent (OPA Engine)            |  |
|  |   - Evaluates Rego Policies against Input Payload   |  |
|  +-----------------------------------------------------+  |
+-----------------------------+-----------------------------+
                              |
+-----------------------------+-----------------------------+
|                                                           |
v                                                           v
[ Action Allowed ]                            [ Action Denied / Escalated ]
Execute API/Database                          Return Policy Violation Error

## Policy Enforcement Mechanics
* **Evaluation:** Evaluates in-flight JSON payloads deterministically prior to downstream execution.
* **Risk-Tiered Escalation:** Categorizes tool calls by financial/operational risk; automatically requires Human-in-the-Loop (HITL) multi-factor confirmation for tier-1 actions.
* **Dynamic Schema Validation:** Verifies structural type matching and runtime boundary checks independent of LLM prompt state.

* ## Interactive Verification & Playground
You can test this policy live without installing OPA via the official OPA Playground:
* **Interactive Demo:** [Open in OPA Playground](https://play.openpolicyagent.org/p/g_ODA0OTg2YzlhZTYzMzE3YTJhZjY4NjkxNzZmMDkwMGZfpWGeFGMJwy7aT6JFf2TaVe1hzPU)

---
*Created as part of an independent R&D initiative in AI Safety, Policy-as-Code, and Enterprise Governance.*

