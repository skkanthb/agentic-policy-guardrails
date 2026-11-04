# agentic-policy-guardrails

# Agentic Policy Guardrails: Deterministic Control Planes for Autonomous LLM Agents

## Overview
As autonomous AI agents shift from passive text generation to transactional execution (calling APIs, executing SQL queries, and interacting via protocols like Model Context Protocol / MCP), non-deterministic LLM behavior introduces severe enterprise security risks. 

This repository provides an architectural blueprint and reference Policy-as-Code implementation using **Open Policy Agent (OPA/Rego)** to intercept and evaluate agent tool calls on the wire—enforcing deterministic enterprise security boundaries before database or API execution.

## Threat Model & Failure Modes Addressed
1. **Unsanitized Payload Mutation:** AI agents passing out-of-bounds numerical arguments (e.g., credit overrides exceeding managerial thresholds).
2. **System Prompt Injection / Drift:** Malicious context manipulation forcing agents to invoke unprivileged tools.
3. **Privilege Escalation:** Agents attempting high-risk operations (in this prototype, credit-limit updates above $50,000) without human approval. These are blocked and returned as requiring approval. Approval tokens are not verified in this prototype, so blocked requests cannot complete through it.
4. **Malformed Tool Calls:** Agents sending missing, renamed, mistyped or extra fields that a policy could misread.

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
* **Threshold Escalation:** Credit-limit updates above $50,000 from an authorized role are blocked and returned with `require_hitl: true`. There is no approval or resume flow in this prototype.
* **Input Validation:** The policy denies any request it cannot fully check: unknown top-level fields; a parameter set that does not exactly match the tool; a `new_limit` that is not a number greater than 0; an empty or non-string `account_id`; an unauthorized role. Every reason is returned in a `violations` list.
* **Endpoint Binding:** `/api/v1/credit` accepts `tool_name: "update_credit_limit"` only. Any other tool name is refused before the policy is evaluated.
* **Field Allow-Listing:** After an allow, the downstream system receives only `user_role`, `tool_name`, `parameters.account_id` and `parameters.new_limit`.
* **Failure Reporting:** If the policy engine is unreachable, nothing is forwarded (HTTP 500). If the downstream call fails or returns an error, the proxy returns HTTP 502 and does not report success.

## Edge-Case Tests
`tests/edge_cases/` contains 32 malformed and unexpected payloads (`cases.jsonl`), one added case (`cases_extra.jsonl`), and scripts that run them against the policy alone (`run_policy_cases.sh`) and through the proxy to a mock target that logs every request it receives (`run_proxy_cases.sh`, `mock_target.py`). CI runs the policy cases and the proxy unit tests on every push and pull request to `main`.

Results on a local mock target, OPA 1.20.1 (files in `tests/edge_cases/`):

| | Before (`996c4f1`) | After (`522d9e9`) |
|---|---|---|
| Policy decisions differing from the intended outcome | 18 of 32 | 0 of 32 |
| Payloads intended to be denied or sent for approval that reached the target | 11 | 0 |
| Target down after an allow | HTTP 200 `SUCCESS` | HTTP 502 `ERP_CALL_FAILED` |
| Policy engine down | HTTP 500, nothing forwarded | HTTP 500, nothing forwarded |

Run the policy cases (requires `jq`):
```
tests/edge_cases/run_policy_cases.sh opa policies/agent_governance.rego tests/edge_cases/cases.jsonl /tmp/policy_results.csv
```

## Known Limitations
* `user_role` and `tool_name` are stated by the caller. There is no identity verification.
* Approval tokens are not verified. Requests above the threshold cannot complete through the proxy.
* No upper bound on `new_limit`.
* The caller's HTTP headers are passed through to the downstream system.
* One policy and one endpoint, tested against a local mock target.

## Interactive Verification & Playground
You can test the policy logic without installing OPA via the official OPA Playground. The Playground link below is a snapshot shared before the edge-case fixes and shows the policy as it was then:
* **Interactive Demo:** [Open in OPA Playground](https://play.openpolicyagent.org/p/g_ODA0OTg2YzlhZTYzMzE3YTJhZjY4NjkxNzZmMDkwMGZfpWGeFGMJwy7aT6JFf2TaVe1hzPU)

---
*Created as part of an independent R&D initiative in AI Safety, Policy-as-Code, and Enterprise Governance.*

