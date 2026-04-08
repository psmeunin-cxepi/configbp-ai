# A2A Audit Report: Assessments – Health Risk Insights

**Source:** `CXEPI/cxp-health-risk-insights-ai` → `a2a_server/config/agent_card.py` (main @ e947f3b)  
**Audit date:** 2026-04-08  
**Overall Status:** WARNING

## 1. Protocol Compliance

| Field | Result | Evidence | Fix |
|---|---|---|---|
| `url` | **FAIL** | `url=A2A_BASE_URL` — v1 proto has no top-level `url` on `AgentCard`. Required field is `supported_interfaces` (repeated `AgentInterface` with `url`, `protocol_binding`, `protocol_version`). | Replace `url=` with `supported_interfaces=` list containing at least one `AgentInterface`. |
| `capabilities.state_transition_history` | **WARNING** | `state_transition_history=False` — not in v1 `AgentCapabilities` proto (only `streaming`, `push_notifications`, `extensions`, `extended_agent_card`). | Remove `state_transition_history`. |
| `skills[*].id` | PASS | Both skills provide `id`. | — |
| `skills[*].name` | PASS | Both skills provide `name`. | — |
| `skills[*].description` | PASS | Both skills provide non-empty `description`. | — |
| `skills[*].tags` | PASS | Both skills provide non-empty `tags`. | — |
| `name` | PASS | Present. | — |
| `description` | PASS | Present. | — |
| `version` | PASS | `"1.0.0"` | — |
| `capabilities` | PASS | Present. | — |
| `default_input_modes` | PASS | `["text/plain"]` | — |
| `default_output_modes` | PASS | `["text/plain"]` | — |
| `skills` | PASS | Two skills defined. | — |

## 2. Routing Quality Heuristics

| Field | Result | Observation | Suggested Improvement |
|---|---|---|---|
| `AgentCard.description` | WARNING | "An intelligent AI agent specializing in…" — promotional filler. Long inventory buries routing signal. | Shortened to 1–2 sentences with explicit routing boundary. |
| `skills[0].description` | WARNING | 54-word run-on listing every sub-capability. Hard for a router to extract primary intent. | Condensed to action-target-outcome pattern. |
| `skills[1].description` | PASS | Reasonably scoped to single asset. | Added "identified by hostname or asset ID" for input clarity. |
| `skills[0].tags` | WARNING | `cisco-health-risk` overlaps with `health-risk`. Missing user-intent verbs/synonyms. | Replaced with `risk-breakdown`, `remediation-priority`, `asset-risk-distribution`. |
| `skills[1].tags` | WARNING | `health-risk` duplicates skill 0 tag — routing ambiguity. Missing `device`, `hostname`. | Added `device`, `hostname`, `single-asset-detail`; dropped `health-risk`. |
| `skills[0].examples` | PASS | Four concrete, distinct, realistic prompts. | — |
| `skills[1].examples` | PASS | Two concrete prompts. | Added third example for broader coverage. |
| Skill overlap | WARNING | Both skills share `health-risk` tag and similar language. Router may struggle with aggregate vs. single-asset. | Tags and descriptions now draw clear boundary. |

## 3. House Rules

Not Applied.

## 4. Critical Issues

1. **Missing `supported_interfaces`** — card uses legacy `url` field not in v1 proto. Any v1-compliant consumer validating against the normative schema will reject the card.
2. **Non-standard `state_transition_history`** — should be removed from `capabilities`.
3. **Routing ambiguity between skills** — overlapping `health-risk` tag and similar description phrasing may cause mis-routing between aggregate and single-asset queries.
