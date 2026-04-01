# Analysis: "Show me a summary of the latest assessment result"

**Problem:** User expected "latest" to mean the single most recent execution run. The agent returned combined results across all 9 executions.

**Trace:** [LangSmith Public Trace](https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/28cb1e11-18de-42fb-b2d0-03f3164f5661/r)

---

## 1. Trace Overview

| Field | Value |
|---|---|
| Trace ID | `019d43df-7d61-7dc3-9a15-734fa274e1c2` |
| Model | `gpt-5.3-chat-2026-03-03` |
| Provider | OpenAI (via AI Framework Serving) |
| Revision | `v1.0.70-3-g6377977` |
| Status | Success |
| Total Duration | ~39s (12:30:13 → 12:30:52 UTC) |
| Total Tokens | 10,202 (3,540 + 6,404 prompt / 64 + 194 completion) |
| LLM Calls | 2 |
| Tool Calls | 2 (parallel) |

### Run Tree

```
graph (root chain) — 39s
├── intent_classifier (step 1) — chain
├── assistant (step 2) — 8s → LLM call #1
│   └── LLM: 3,540 prompt + 64 completion → 2 tool_calls
├── tools (step 3) — 17s
│   ├── query_findings(include_execution_overview=true) → success
│   └── query_findings(view_mode=distribution, group_by=severity, metrics=[count]) → success
└── assistant (step 4) — 15s → LLM call #2
    └── LLM: 6,404 prompt + 194 completion → final response (stop)
```

---

## 2. Message Flow

### Step 2 — LLM Call #1 (tool selection)

**Input:** User message: `"Show me a summary of the latest assessment result."`

**Output:** Two parallel tool calls:

```json
// Tool call 1
{"name": "query_findings", "args": {"include_execution_overview": true}}

// Tool call 2
{"name": "query_findings", "args": {"view_mode": "distribution", "group_by": "severity", "metrics": ["count"]}}
```

The LLM correctly followed the system prompt's parallel-call strategy. It issued both calls in a single turn.

### Step 3 — Tool Results

**Tool call 1 (execution overview):** Returned 9 execution records — one per management_system_id. The most recent by `finished_at` is:

| Execution ID | management_system_id | finished_at | assets | violations |
|---|---|---|---|---|
| `exec-20260329-193012-ac2780` | `7682439e-...` | 2026-03-29T19:36:06Z | 2 | 148 |

The oldest:

| Execution ID | management_system_id | finished_at | assets | violations |
|---|---|---|---|---|
| `exec-20260326-210048-b40bfb` | `5c965920-...` | 2026-03-26T22:52:42Z | 2 | 148 |

**Tool call 2 (severity distribution):** Returned counts summed across ALL 9 executions:

| Severity | Count |
|---|---|
| MEDIUM | 10,377 |
| HIGH | 1,260 |
| LOW | 1,143 |
| INFORMATIONAL | 540 |
| **Total** | **13,320** |

### Step 4 — LLM Call #2 (final response)

The LLM synthesized both tool results into this response:

> ## Latest Assessment Summary
>
> **Assessment:** Default Assessment
> **Execution ID:** exec-20260329-193012-ac2780
> **Completed At:** 2026-03-29 19:36:06 UTC
> **Status:** Completed
> **Triggered By:** cbp-engine-producer
> **Assets Assessed:** 2
> **Total Violations:** 148
>
> This is the most recent execution among the latest assessment runs.
>
> ## Severity Distribution
>
> | Severity | Findings |
> |---|---|
> | High | 1,260 |
> | Medium | 10,377 |
> | Low | 1,143 |
> | Informational | 540 |
> | Critical | No findings returned |
>
> **Total Findings Across Latest Execution Set:** 13,320

---

## 3. The Problem: Inconsistent Scoping

The LLM's response is **internally contradictory**:

- **Header section:** Correctly identifies the single most recent execution (`exec-20260329-193012-ac2780`) with **2 assets** and **148 violations**
- **Severity distribution section:** Shows **13,320 total findings** — which is the combined count across ALL 9 executions, not the 148 from the single most recent one

The user sees "Latest Assessment Summary" with "148 violations" immediately followed by a severity breakdown totaling 13,320. This is confusing because the numbers don't align — the summary implies one execution but the distribution covers all nine.

### Why this happened

The problem has **two contributing layers**:

#### Layer 1: MCP Server — `resolve_latest_executions` always returns ALL management systems

Every `query_findings` call unconditionally calls `resolve_latest_executions` (`query_builder.py:118-145`), which runs:

```sql
SELECT t.management_system_id, t.latest_execution_id, e.finished_at
FROM configuration_customer_connector_execution_track t
LEFT JOIN configuration_assessment_execution e
    ON e.execution_id = t.latest_execution_id
   AND e.platform_account_id = t.platform_account_id
WHERE t.platform_account_id = ?
ORDER BY t.management_system_id
```

This returns **one execution per management_system_id** — the latest execution for each connector/upload type. For this account, that's 9 rows. **There is no parameter to filter to a single management system or a single execution.**

All subsequent queries (severity distribution, aggregates, etc.) use `WHERE execution_id IN (all 9 IDs)`. The MCP server has no concept of "the single most recent execution" — it always scopes to the full set of latest-per-management-system.

#### Layer 2: LLM — No tool exists to query a single execution's findings

The LLM correctly identified the most recent execution from the overview data. But when it called `query_findings` with `view_mode=distribution`, there was **no way to filter to just that one execution ID**. The `query_findings` tool does not accept an `execution_id` parameter — execution scope is always server-resolved via `resolve_latest_executions`.

The LLM had two choices:
1. Report only the execution overview (148 violations for the most recent) and skip the severity breakdown
2. Report the severity breakdown knowing it covers all 9 executions

It chose option 2 but presented it alongside the single-execution summary, creating the mismatch.

#### Layer 3: System Prompt — Reinforces the combined view

The system prompt (`assessments-configuration-summary.md`) instructs:

> **Objective:** Provide latest assessment summaries, severity distributions, top impacted assets or rules, and answer broad overview questions across **the latest findings**.
>
> **Scope:** Latest assessment summaries and execution context [...] Broad overview questions about **the latest assessment**

The phrase "the latest findings" and "the latest assessment" are ambiguous. The prompt doesn't clarify whether "latest" means:
- (a) The most recently completed single execution (what the user expected)
- (b) The set of latest-per-management-system executions (what the tools return)

The MCP tools implement interpretation (b). The user expected interpretation (a).

---

## 4. Where the Fault Lies

| Layer | Component | Issue |
|---|---|---|
| **MCP Server** | `resolve_latest_executions` | No option to return only the single most recent execution globally; always returns one per management_system_id |
| **MCP Server** | `query_findings` tool API | No `execution_id` parameter to allow the LLM to scope queries to a specific execution |
| **System Prompt** | `assessments-configuration-summary.md` | "Latest" is ambiguous; doesn't explain the multi-execution-per-management-system data model |
| **LLM** | Response synthesis | Mixed single-execution metadata with all-execution aggregates without clearly flagging the scope mismatch |

### Primary root cause

**The MCP server's data model defines "latest" as "the set of latest executions across all management systems" — not "the single most recent execution."** The tools enforce this interpretation at the SQL level with no override mechanism. The LLM cannot work around this even if it understands the user's intent.

---

## 5. Possible Fixes

### Option A: Add execution_id filter to query_findings (MCP Server change)

Add an optional `execution_id` or `execution_ids` parameter to `query_findings`. When provided, skip `resolve_latest_executions` and use the caller-supplied IDs directly in the `WHERE execution_id IN (...)` clause.

**Flow with fix:**
1. LLM calls `query_findings(include_execution_overview=true)` → gets all 9 executions
2. LLM identifies the most recent: `exec-20260329-193012-ac2780`
3. LLM calls `query_findings(execution_id="exec-20260329-193012-ac2780", view_mode="distribution", group_by="severity", metrics=["count"])`
4. Severity distribution now correctly scoped to that single execution (148 findings)

**Pros:** Most flexible; enables any execution-scoped query. No prompt changes needed.
**Cons:** Requires MCP server code change. Adds a two-turn interaction (overview first, then scoped query).

### Option B: Add management_system_id filter to query_findings (MCP Server change)

Since "latest" means latest-per-management-system, allow filtering by management_system_id to scope to a single connector's execution.

**Pros:** Aligns with the existing data model.
**Cons:** Still requires the LLM to know which management_system_id to filter to; user said "latest" not a connector name.

### Option C: System prompt clarification (No code change)

Update the system prompt to explicitly instruct the LLM:

> "The tools return data scoped to the latest execution set — one execution per management system (connector). When the user asks about 'the latest' assessment result, present the execution overview first, then clarify that aggregates (severity distribution, top assets, etc.) cover the full execution set of N management systems, not just the single most recent execution."

**Pros:** No code changes required.
**Cons:** The LLM still cannot show a severity breakdown for a single execution. It can only describe the mismatch, not fix it.

### Option D: Hybrid (Recommended)

1. **Add `execution_ids` parameter** to `query_findings` (Option A) — enables precise scoping
2. **Update system prompt** to include guidance on when to use execution-scoped queries vs. full-set queries

This gives the LLM both the tooling and the instructions to correctly handle "latest" as the user intended.

---

## 6. Token Analysis

| LLM Call | Step | Prompt Tokens | Completion Tokens | Total | Cache Hit |
|---|---|---|---|---|---|
| #1 (tool selection) | 2 | 3,540 | 64 | 3,604 | 0% |
| #2 (response synthesis) | 4 | 6,404 | 194 | 6,598 | 0% |
| **Total** | | **9,944** | **258** | **10,202** | **0%** |

- No prompt caching on either call (0 `cached_tokens`). The second call includes the full tool results (~2,864 additional tokens from tool outputs).
- Completion tokens are modest (258 total). The cost is dominated by prompt tokens.
- Zero reasoning tokens — model used direct generation without chain-of-thought.

---

## 7. Summary

The user asked for "the latest assessment result." The agent returned a header scoped to the single most recent execution (148 violations) but a severity distribution scoped to all 9 executions (13,320 findings). This inconsistency stems from the MCP server's `resolve_latest_executions` always returning the full set of latest-per-management-system executions, with no mechanism for the LLM to scope subsequent queries to a single execution.

**Recommended fix:** Add an optional `execution_ids` parameter to `query_findings` so the LLM can scope queries to specific executions after reviewing the execution overview.
