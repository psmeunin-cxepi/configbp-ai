# A2A Audit Report: Assets (General)

**Source:** `CXEPI/cvi-ldos-ai` → `a2a/server.py` + `a2a/skills.py` (main)  
**Audit date:** 2026-04-08  
**Overall Status:** FAIL

## 1. Protocol Compliance

| Field | Result | Evidence | Fix |
|---|---|---|---|
| `url` | **FAIL** | `url=base_url` — v1 proto has no top-level `url` on `AgentCard`. | Replace with `supported_interfaces`. |
| `supported_interfaces` | **FAIL** | Missing. REQUIRED repeated field. | Add `supported_interfaces=[AgentInterface(...)]`. |
| `preferred_transport` | **FAIL** | `preferred_transport="JSONRPC"` — not in v1 schema. | Remove; express via `supported_interfaces[].protocol_binding`. |
| `name` | PASS | `"Assets (General)"` | — |
| `description` | PASS | Present, non-empty. | — |
| `version` | PASS | `"1.0.0"` | — |
| `capabilities` | PASS | `AgentCapabilities(streaming=True)` | — |
| `default_input_modes` | PASS | `["text/plain"]` | — |
| `default_output_modes` | PASS | `["text/plain"]` | — |
| `skills` | PASS | Two skills. | — |
| `skills[0].id` | PASS | `"ask_cvi_ldos_ai_internal"` | — |
| `skills[0].name` | PASS | Present. | — |
| `skills[0].description` | PASS | Non-empty. | — |
| `skills[0].tags` | PASS | 3 tags. | — |
| `skills[1].id` | PASS | `"ask_cvi_ldos_ai_external"` | — |
| `skills[1].name` | PASS | Present. | — |
| `skills[1].description` | PASS | Non-empty. | — |
| `skills[1].tags` | PASS | 3 tags. | — |

## 2. Routing Quality Heuristics

| Field | Result | Observation | Suggested Improvement |
|---|---|---|---|
| `AgentCard.description` | **WARNING** | ~40+ lines. Reads like a product spec with markdown headers, bullet inventories, and negative routing rules. LLM router cannot efficiently extract core intent. | Compressed to 2–3 sentences with explicit routing boundary vs. Asset Criticality agent. |
| `skills[0].tags` | **WARNING** | `sav_id` is opaque internal key. `iq_internal` is internal jargon. Only 3 tags — low match surface. | Replaced with user-intent terms: `asset-inventory`, `lifecycle`, `ldos`, etc. (10 tags). |
| `skills[1].tags` | **WARNING** | Same issues: `sav_id`, `iq_external`. Only 3 tags. | Replaced with user-intent terms (10 tags). |
| `skills[0].name` | **WARNING** | "Ask CVI LDOS AI (Internal)" — `CVI` is opaque. "(Internal)" leaks architecture. | Renamed to `"Asset Lifecycle Analysis (Internal)"`. |
| `skills[1].name` | **WARNING** | "Ask CVI LDOS AI" — same `CVI` issue. | Renamed to `"Asset Lifecycle Analysis"`. |
| Skill overlap | **WARNING** | Skills 0 and 1 have near-identical descriptions and overlapping examples. Distinction is internal-vs-external audience — an authorization concern, not capability. | Noted as architectural risk. Descriptions now clarify data-scope difference. |
| `skills[0–1].examples` | PASS | 13 and 16 examples — concrete, diverse, well-aligned. | — |

## 3. House Rules

Not Applied.

## 4. Critical Issues

1. **Missing `supported_interfaces` + legacy `url`/`preferred_transport`** — card rejected by v1-compliant consumer.
2. **Description is a multi-page spec** — overwhelms the router; routing signal buried under ~40 lines.
3. **Two skills differing only by audience** — routing ambiguity; internal-vs-external is an authz decision, not a capability distinction.
