# A2A Audit Report: Assessments – Configuration

**Source:** `CXEPI/configbp-ai` → `a2a_server/config/agent_card.py` (main branch)
**Audited:** 2026-04-08
**Schema Reference:** [A2A v1 Proto Definition](https://a2a-protocol.org/latest/definitions/)

**Overall Status:** FAIL

## 1. Protocol Compliance

| Field | Result | Evidence | Fix |
|---|---|---|---|
| `supported_interfaces` | **FAIL** | Field missing entirely | Add `supported_interfaces` with at least one `AgentInterface` containing `url`, `protocol_binding`, and `protocol_version` |
| `url` | **FAIL** | `url=A2A_SERVER_URL` set on AgentCard | Remove. The v1 `AgentCard` proto has no top-level `url` field; move the URL into `supported_interfaces[0].url` |
| `capabilities.state_transition_history` | **WARNING** | `state_transition_history=False` | Remove. The v1 `AgentCapabilities` message defines `streaming`, `push_notifications`, `extensions`, and `extended_agent_card` only. `state_transition_history` was a pre-v1 field |

**Summary:** The card is built against a **pre-v1 SDK/schema**. The two FAIL items — missing `supported_interfaces` and use of the removed top-level `url` — make this card non-compliant with the v1 proto definition. All four skills pass internal schema checks (`id`, `name`, `description`, `tags` all present and non-empty).

## 2. Routing Quality Heuristics

| Field | Result | Observation | Suggested Improvement |
|---|---|---|---|
| `AgentCard.description` | **WARNING** | 7-line inventory listing all four skills; reads like a feature matrix, not a routing signal | Replace with 1–2 sentences: what the agent does well, and where to stop routing here. Let the skills carry the detail |
| `skills[0].description` (assessments-configuration-summary) | **MINOR** | Solid but front-loads internal data taxonomy ("pass/fail rates, technology and category breakdowns…") before the user-facing value | Lead with the user question it answers, then mention the data dimensions |
| `skills[1].description` (asset-scope-analysis) | **WARNING** | Lists 20+ filterable dimensions inline, making the description hard to scan for a router | Summarise as "filterable by hostname, product family, location, software version, contract, and 15+ other dimensions" and keep the full list in tags or docs |
| `skills[1].tags` | **MINOR** | Includes very specific dimensions (`coverage`, `lifecycle`, `criticality`) that are useful, but also includes `scope` and `filter` which are generic verbs unlikely to disambiguate | Replace `scope`/`filter` with domain terms like `remediation` or `violation` |
| `skills[2].tags` (rule-analysis) | **MINOR** | `configuration` and `compliance` overlap with the agent-level domain | Consider replacing with more specific terms: `rule-id`, `rule-category`, `cross-rule-comparison` |
| `skills[3].description` (signature-asset-insights) | **OK** | Concise and well-scoped | — |
| `skills[3].examples` | **MINOR** | 4 examples are very similar in phrasing ("Show insights…", "What are the top…", "Summarize…", "What should I focus on…") | Diversify: add a question about a specific insight ID or filtering by priority level |
| **Cross-skill overlap** | **WARNING** | `assessments-configuration-summary` mentions "top impacted assets ranked by violation count" while `asset-scope-analysis` covers per-asset violations. A router could misroute a query like "which assets have the most violations?" | Sharpen the boundary: summary = aggregate counts/distributions; asset-scope = per-device drill-downs. Reflect this in descriptions |

## 3. House Rules

Not Applied.

## 4. Critical Issues

1. **`supported_interfaces` missing / `url` is non-v1** — blocks protocol compliance entirely. Must migrate from `url=` to `supported_interfaces=[AgentInterface(...)]`.
2. **`AgentCard.description` is an inventory, not a routing signal** — an LLM router reading this alongside other agent cards will struggle to quickly decide whether to route here vs. a neighboring agent.
3. **Summary ↔ Asset-Scope skill boundary is blurry** — "top impacted assets" appears in the summary skill while asset-level analysis is the explicit purpose of skill #2. This creates a routing collision.

## 5. Revised AgentCard

See `agent_card_v1.py`.
