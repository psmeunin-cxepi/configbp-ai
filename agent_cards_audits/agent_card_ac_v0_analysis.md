# A2A Audit Report: Asset Criticality

**Source:** `CXEPI/cvi-ldos-ai` → `a2a/server.py` + `a2a/skills.py` (main)  
**Audit date:** 2026-04-08  
**Overall Status:** FAIL

## 1. Protocol Compliance

| Field | Result | Evidence | Fix |
|---|---|---|---|
| `url` | **FAIL** | `url=base_url` — v1 proto has no top-level `url` on `AgentCard`. | Replace with `supported_interfaces`. |
| `supported_interfaces` | **FAIL** | Missing. REQUIRED repeated field. | Add `supported_interfaces=[AgentInterface(...)]`. |
| `preferred_transport` | **FAIL** | `preferred_transport="JSONRPC"` — not in v1 schema. | Remove. |
| `name` | PASS | `"Asset Criticality"` | — |
| `description` | PASS | Present, non-empty. | — |
| `version` | PASS | `"1.0.0"` | — |
| `capabilities` | PASS | `AgentCapabilities(streaming=True)` | — |
| `default_input_modes` | PASS | `["text/plain"]` | — |
| `default_output_modes` | PASS | `["text/plain"]` | — |
| `skills` | PASS | One skill. | — |
| `skills[0].id` | PASS | `"ask_asset_criticality"` | — |
| `skills[0].name` | PASS | `"Asset Criticality"` | — |
| `skills[0].description` | PASS | Non-empty, good content. | — |
| `skills[0].tags` | PASS | 6 tags. | — |

## 2. Routing Quality Heuristics

| Field | Result | Observation | Suggested Improvement |
|---|---|---|---|
| `AgentCard.description` | **WARNING** | ~30 lines — spec-level document, too long for router consumption. | Compressed to 2–3 sentences with explicit routing boundary. |
| `skills[0].tags` | **WARNING** | `field_notices` uses underscore; inconsistent with kebab-case in sibling agents. `ldos` overlaps with Assets (General) agent. | Normalized to kebab-case: `field-notices`. Removed `ldos`, added `place-in-network`, `risk-ranking`, `refresh`, `security-advisory`. |
| `skills[0].name` | **WARNING** | Agent name and skill name identical: "Asset Criticality". | Skill renamed to `"Asset Criticality & Risk Prioritization"`. |
| `skills[0].examples` | PASS | 8 concrete, diverse examples well-aligned with criticality/prioritization. | — |
| Cross-agent overlap | **WARNING** | Description mentions LDOS, security advisories, field notices — also in Assets (General). Boundary (criticality angle) is stated but easily missed. | Compressed descriptions sharpen the routing boundary. |

## 3. House Rules

Not Applied.

## 4. Critical Issues

1. **Missing `supported_interfaces`** — v1 protocol breach.
2. **Description length** — too long for efficient routing.
3. **Cross-agent tag overlap with Assets (General) on `ldos`** — router may match both agents on LDOS queries.
