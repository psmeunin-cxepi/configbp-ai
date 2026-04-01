# Analysis: "Show Cat9k deviations" — Asset Scope Mismatch

**Problem:** User asked about Cat9k devices. The agent called `search_assets_scope` with `product_family=["Cat9k"]`, received a "success" response, then used that scope in `query_findings` — which returned 0 results because `"Cat9k"` doesn't match any `product_family` value in the database.

**Trace:** [LangSmith Public Trace](https://langsmith.nprd.usw2.plat.cxp.csco.cloud/public/b831d157-16b5-46c5-a292-f237a4b9d610/r)

---

## 1. Trace Overview

| Field | Value |
|---|---|
| Trace ID | Root chain "Configuration Agent" |
| Model | gpt-5.3-chat-2026-03-03 |
| Effective Intent | `asset-scope-analysis` |
| System Prompt | `asset-scope-analysis.md` |
| Status | Success |
| Total Duration | ~29.5s (09:55:16 → 09:55:45 UTC) |
| Total Tokens | 13,319 (12,947 prompt / 372 completion) |
| LLM Calls | 3 |
| Tool Calls | 5 (across 2 tool rounds) |

### Input

The graph received two input messages. The `system` message carried prior conversation context (the agent had already asked the user to specify a product family), and the `human` message was the user's follow-up:

**system** (conversation context):
> Recent conversation context:
> [user] Show deviations for a specific product family
> [Assessments – Configuration] Understanding your request...
> [Assessments – Configuration] Thinking about your question...
> [Assessments – Configuration] To show deviations, I need to scope the query to a specific **product family**.
>
> Which **product family** should I analyze?
> For example: `PowerEdge`, `Unity`, `Isilon`, etc.
>
> Once you provide it, I'll pull the deviation (violated findings) details for that product family.

**human:**
> Cat9k

### Output

The agent's final response to the user:

> ## Asset Scope
> **Product Family:** Cat9k
>
> ## Summary
> No configuration deviations (violated findings) were returned for assets in the **Cat9k** product family in the **latest assessment set**.
>
> ## Findings
> The query for findings with status **VIOLATED** returned **0 results** for this asset scope.
>
> ## Failed Rules
> No failed rules were detected for Cat9k assets in the latest assessment.
>
> ## Severity Breakdown
> No violated findings were returned, so there is **no severity distribution** for this scope.
>
> If you'd like, I can also:
> - Show **all findings (including compliant ones)** for Cat9k
> - Break results down **by asset/hostname**
> - Identify **top rules evaluated** for Cat9k assets.

### Run Tree

```
Configuration Agent (root chain) — 29.5s
├── flow_router (step 1) — instant
├── assistant (step 2) — 9.6s → LLM call #1
│   └── 3,874 prompt + 93 completion → 1 tool_call
├── tools (step 3) — 0.09s
│   └── search_assets_scope(product_family=["Cat9k"]) → success (echo)
├── assistant (step 4) — 7.4s → LLM call #2
│   └── 3,918 prompt + 120 completion → 3 tool_calls
├── tools (step 5) — 2.7s
│   ├── search_assets_scope(product_family=["Cat9k"]) → success (echo)
│   ├── query_findings(asset_scope={product_family:["Cat9k"]}, group_by=rule, ...) → 0 results
│   └── query_findings(asset_scope={product_family:["Cat9k"]}, group_by=severity, ...) → 0 results
└── assistant (step 6) — 9.7s → LLM call #3
    └── 5,155 prompt + 159 completion → final response (stop)
```

---

## 2. Message Flow

### Step 2 — LLM Call #1

**Input:** User message (via A2A, effective_intent=`asset-scope-analysis`)

**Output:** Single tool call to resolve asset scope:

```json
{"name": "search_assets_scope", "args": {"product_family": ["Cat9k"]}}
```

The LLM correctly followed the system prompt's instruction: *"Resolve asset scope first, then query findings."*

### Step 3 — Tool Response: search_assets_scope

**Response:**
```json
{"product_family": ["Cat9k"]}
```

**Status:** `success`

This is the **root cause**. `search_assets_scope` is a **validation-only** tool that normalizes input without querying the database. It returned `"Cat9k"` unchanged — confirming it as a "valid" scope. The LLM received no signal that `"Cat9k"` doesn't match any actual `product_family` value in the database.

### Step 4 — LLM Call #2

**Output:** Three parallel tool calls:

```json
// Tool call 1 — redundant re-call of search_assets_scope
{"name": "search_assets_scope", "args": {"product_family": ["Cat9k"]}}

// Tool call 2 — findings by rule
{"name": "query_findings", "args": {
  "asset_scope": {"product_family": ["Cat9k"]},
  "view_mode": "aggregate",
  "group_by": "rule",
  "metrics": ["violations_count", "distinct_assets", "critical_count", "high_count"],
  "status_in": ["VIOLATED"],
  "limit": 50
}}

// Tool call 3 — severity distribution
{"name": "query_findings", "args": {
  "asset_scope": {"product_family": ["Cat9k"]},
  "view_mode": "distribution",
  "group_by": "severity",
  "status_in": ["VIOLATED"]
}}
```

**Observation:** The LLM called `search_assets_scope` a second time with the same input — wasteful but harmless.

### Step 5 — Tool Responses

All three tools returned successfully. Both `query_findings` calls returned:

```json
{
  "meta": {
    "asset_scope_applied": true,
    "filters_applied": {"status_in": ["VIOLATED"]},
    "pagination": {"limit": 50, "offset": 0, "total": 0}
  },
  "data": {
    "records": [],
    "aggregates": []
  }
}
```

**`total: 0`** — Zero findings matched.

### Step 6 — LLM Call #3 (Final Response)

The LLM attempted ANOTHER round of the same 3 tool calls (search_assets_scope + 2x query_findings with identical arguments). However, since `finish_reason` was `stop`, it generated the final response:

> ## Asset Scope
> **Product Family:** Cat9k
>
> ## Summary
> No configuration deviations (violated findings) were returned for assets in the **Cat9k** product family in the **latest assessment set**.
>
> ## Findings
> The query for findings with status **VIOLATED** returned **0 results** for this asset scope.
>
> [...]

The LLM correctly reported "0 results" based on tool output — it followed the grounding rules. But the underlying data issue went undetected.

---

## 3. Root Cause Analysis

### Why "Cat9k" returned 0 results

The `asset_scope` filter generates this SQL condition (in `_build_asset_scope_conditions`):

```sql
lower(a.product_family) IN ('cat9k')
```

The database contains 93 distinct `product_family` values. The Catalyst 9000 entries are:

| Actual DB value |
|---|
| Cisco Catalyst 9200 Series Switches |
| Cisco Catalyst 9300 Series Switches |
| Cisco Catalyst 9400 Series Switches |
| Cisco Catalyst 9500 Series Switches |
| Cisco Catalyst 9600 Series Switches |
| Cisco Catalyst 9800 Series Wireless Controllers |
| Cisco Catalyst 9800 Wireless Controllers for Cloud |
| Catalyst 9K Series Fans |
| Catalyst 9K Series Modules |
| Catalyst 9K Series Power Supplies |
| Catalyst 9K Series Supervisor Modules |

`"cat9k"` does not match any of these. The filter uses **exact `IN` matching** (case-insensitive), not `LIKE` or fuzzy search.

### The `search_assets_scope` design gap

| Aspect | Current behavior | Expected behavior |
|---|---|---|
| DB validation | None — normalizes input only | Should validate against actual DB values |
| Fuzzy matching | None | Should support partial/fuzzy matching |
| Response on invalid value | Echoes input back as "success" | Should return an error or suggest closest matches |
| Tool docstring | *"validation-only: returns normalized scope data without performing any asset lookup against Trino"* | Misleading — "validation" implies checking validity |

The tool's docstring explicitly states it does no DB lookup. However, the LLM has no way to know this from the tool's external description. The tool description presented to the LLM says:

> *Resolve and normalize asset scope filters for use in downstream queries*

The LLM reasonably interpreted a "success" response as confirmation that Cat9k assets exist.

### Contributing factors

| # | Layer | Issue |
|---|---|---|
| 1 | **`search_assets_scope` tool** | Does not query DB; echoes any input as "valid" — even non-existent values |
| 2 | **Asset scope filter** | Uses exact `IN` matching — no fuzzy/partial matching for natural-language abbreviations |
| 3 | **System prompt** | Tells LLM to "resolve asset scope first" but the tool doesn't actually resolve anything |
| 4 | **LLM** | Used the abbreviation "Cat9k" instead of the full product family name — reasonable for a user-facing agent but incompatible with the exact-match filter |
| 5 | **`query_findings` response** | Returns `total: 0` with no diagnostic hint about why the scope matched nothing |

---

## 4. Comparison with Previous Analysis

This problem compounds with the issue identified in [ANALYSIS_latest_assessment_summary_trace.md](ANALYSIS_latest_assessment_summary_trace.md):

| Issue | Previous trace | This trace |
|---|---|---|
| Problem | "Latest" means all 9 executions, not the single most recent | "Cat9k" doesn't match any DB values |
| Root cause layer | MCP Server (`resolve_latest_executions` returns all) | MCP Server (`search_assets_scope` doesn't validate) |
| LLM behavior | Correctly followed tool output | Correctly followed tool output |
| Tool API gap | No `execution_id` filter parameter | No DB-backed validation or fuzzy matching |
| User impact | Misleading combined metrics | False "no results" response |

Both problems share a common pattern: **the MCP tools don't provide enough semantic intelligence for the LLM to make correct decisions.** The tools return technically correct responses (no errors), but the data doesn't match user intent.

---

## 5. Proposed Fixes

### Fix A: Add DB validation to `search_assets_scope` (Recommended)

Modify `search_assets_scope` to query the `cvi_assets_view` table and validate that the provided scope values actually exist. For list fields like `product_family`:

1. Query: `SELECT DISTINCT product_family FROM cvi_assets_view WHERE platform_account_id = ? AND lower(product_family) IN (?)`
2. If exact match found → return matched values
3. If no exact match → fall back to fuzzy search: `SELECT DISTINCT product_family FROM cvi_assets_view WHERE platform_account_id = ? AND lower(product_family) LIKE ?`
4. Return: `{"product_family": ["Cisco Catalyst 9400 Series Switches", ...], "matched_by": "fuzzy", "original_query": ["Cat9k"]}`

**Pros:** Solves the problem at the source; LLM gets correct DB values before downstream queries.
**Cons:** Adds DB round-trip to what is currently instant; scope tool becomes stateful.

### Fix B: Add fuzzy/LIKE matching to asset_scope filters

Change `_build_asset_scope_conditions` to use `LIKE` with wildcards when exact match returns 0 results, or always use LIKE for certain fields.

**Pros:** Tolerant of abbreviations.
**Cons:** May over-match; changes behavior for all scope-filtered queries; harder to explain to LLM what matched.

### Fix C: Add a "discover" mode to search_assets_scope

Add a parameter like `discover=true` that queries the DB for available values of a given field:

```json
{"name": "search_assets_scope", "args": {"product_family": ["Cat9k"], "discover": true}}
```

Returns: available product_family values matching "Cat9k" (fuzzy), along with counts.

**Pros:** Backward compatible; explicit opt-in.
**Cons:** LLM needs to know when to use discover mode.

### Fix D: System prompt guidance (No code change)

Update `asset-scope-analysis.md` to warn the LLM:

> "Product family values must be exact matches. If the user provides an abbreviation (e.g., 'Cat9k'), you should ask the user for the full product family name or use query_findings with group_by='product_family' to discover available values."

**Pros:** No code changes.
**Cons:** LLM still can't discover valid values; shifts burden to user.

### Fix E: Hybrid (Recommended)

1. **Fix A** — DB validation in `search_assets_scope` with fuzzy fallback
2. Update system prompt to note that `search_assets_scope` validates against actual DB values

---

## 6. Token Analysis

| LLM Call | Step | Prompt | Completion | Total | Purpose |
|---|---|---|---|---|---|
| #1 | 2 | 3,874 | 93 | 3,967 | Resolve scope |
| #2 | 4 | 3,918 | 120 | 4,038 | Query findings (3 parallel tools) |
| #3 | 6 | 5,155 | 159 | 5,314 | Final response |
| **Total** | | **12,947** | **372** | **13,319** | |

- 3 LLM round-trips for a query that returned 0 results — waste caused by the silent validation failure
- 0% prompt cache hit rate across all calls
- The redundant `search_assets_scope` call in Step 4 added tokens without value

---

## 7. Summary

The agent correctly followed its system prompt: resolve asset scope first via `search_assets_scope`, then query findings with that scope. The failure is that `search_assets_scope` is **validation-only in name but not in practice** — it normalizes strings but never checks the database. It returned `"Cat9k"` as a valid scope, causing all downstream queries to silently return 0 results.

The user received a technically correct response ("0 findings for Cat9k") but the answer was semantically wrong — there ARE Catalyst 9000 findings in the DB, they're just stored under full product family names like "Cisco Catalyst 9400 Series Switches."

**Primary fix:** Make `search_assets_scope` query the database to validate scope values and provide fuzzy matching for natural-language abbreviations.
