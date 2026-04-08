# A2A Audit Report: SA AI Reasoning

**Source:** `CXEPI/risk-app` → `sa-ai-reasoning-agent-a2a/server.py` (main)  
**Audit date:** 2026-04-08  
**Overall Status:** FAIL

## 1. Protocol Compliance

| Field | Result | Evidence | Fix |
|---|---|---|---|
| `url` | **FAIL** | `url=base_url` — v1 proto has no top-level `url` on `AgentCard`. Required field is `supported_interfaces`. | Replace with `supported_interfaces=` list containing at least one `AgentInterface`. |
| `supported_interfaces` | **FAIL** | Missing entirely. REQUIRED repeated field in v1. | Add `supported_interfaces=[AgentInterface(url=..., protocol_binding="JSONRPC", protocol_version="1.0")]`. |
| `preferred_transport` | **FAIL** | `preferred_transport="JSONRPC"` — not a field in the v1 `AgentCard` proto. Transport is expressed via `supported_interfaces[].protocol_binding`. | Remove; move intent into `supported_interfaces`. |
| `name` | PASS | `"SA AI Reasoning"` | — |
| `description` | PASS | Present, non-empty. | — |
| `version` | PASS | `"1.0.0"` | — |
| `capabilities` | PASS | `AgentCapabilities(streaming=False)` — valid fields only. | — |
| `default_input_modes` | PASS | `["text/plain"]` | — |
| `default_output_modes` | PASS | `["text/plain"]` | — |
| `skills` | PASS | One skill defined. | — |
| `skills[0].id` | PASS | `"sa_ai_reasoning"` | — |
| `skills[0].name` | PASS | `"SA AI Reasoning"` | — |
| `skills[0].description` | PASS | Non-empty. | — |
| `skills[0].tags` | PASS | 5 tags. | — |

## 2. Routing Quality Heuristics

| Field | Result | Observation | Suggested Improvement |
|---|---|---|---|
| `AgentCard.description` | **WARNING** | Reads as a constraint/filter ("Questions and content must be directly related to…") rather than stating what the agent *does*. The positive capability is buried in the second sentence. | Lead with what the agent does, then state the routing boundary. |
| `skills[0].description` | PASS | Good action-target-outcome pattern. | — |
| `skills[0].tags` | **WARNING** | Uses underscores (`security_assessment`) — inconsistent with kebab-case used by sibling agents. `reasoning` is too generic. Missing user-intent terms like `slic-verification`, `hardening-check`. | Normalized to kebab-case. Replaced `reasoning` with specific tags. |
| `skills[0].examples` | PASS | Four concrete, distinct prompts aligned with the skill boundary. | — |
| Agent name ↔ Skill name | **WARNING** | Agent name and skill name are identical ("SA AI Reasoning"). "SA AI" is opaque internal abbreviation. | Renamed agent to *"Security Assessment – SLIC Reasoning"*, skill to *"SLIC Result Validation"*. |

## 3. House Rules

Not Applied.

## 4. Critical Issues

1. **Missing `supported_interfaces` + non-standard `url` and `preferred_transport`** — three related failures. The card uses two legacy/non-existent fields instead of the required `supported_interfaces` list. A v1-compliant consumer will reject this card.
2. **Description leads with restrictions** — a router reading "Questions must be directly related to…" gets no positive signal about what to route *to* this agent.
