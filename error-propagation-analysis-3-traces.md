# Error Handling Analysis: Non-Deterministic Error Responses Across Identical Failures

**Date:** 2026-03-30
**Traces Analysed:**

| Label | Trace URL | Share Token |
|---|---|---|
| Trace 1 — Verbose retry + internal details | [LangSmith](https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/2ae7e864-c303-4aca-b721-40f8f61d4a6c/r/019d303b-065c-7b42-9f88-975f1c09547c) | `2ae7e864-c303-4aca-b721-40f8f61d4a6c` |
| Trace 2 — Generic one-liner, no retry | [LangSmith](https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/042673d8-68f0-494f-8680-7b08dbc7c2e7/r) | `042673d8-68f0-494f-8680-7b08dbc7c2e7` |
| Trace 3 — Structured status, 1 retry | [LangSmith](https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/90507c0a-3d28-415f-93dc-e68aec2fcd26/r) | `90507c0a-3d28-415f-93dc-e68aec2fcd26` |

**Common Context:**
- **Input:** "Show me a summary of my assessment results"
- **Revision:** `v1.0.58-4-g884fe85`
- **Model:** `gpt-5.3-chat-2026-03-03` (temperature 0.0)
- **Agent:** Configuration Agent
- **Effective intent:** `assessments-configuration-summary`
- **Flow type:** `chat`
- **Failure:** All `query_findings` tool calls return `MCPToolError('An internal server error occurred while executing the tool.')` with `status: error`

---

## Executive Summary

Three executions of the same agent with the same user input all fail identically — every `query_findings` tool call returns a server-side `MCPToolError`. Despite identical failure conditions and `temperature: 0.0`, the agent produces **three fundamentally different responses** with different retry strategies, different levels of internal detail exposure, and different response structures.

This demonstrates five problems:

1. **Non-deterministic error responses** — the LLM generates different error text each time, despite temperature 0.0
2. **Non-deterministic retry behavior** — 0, 1, or 2 retry cycles with no predictable pattern
3. **Non-deterministic initial tool call strategy** — 1, 2, or 4 parallel tool calls on the first attempt
4. **Internal architecture leakage** — 2 of 3 responses name the "findings service" and expose tool error semantics
5. **Misleading error framing** — `"Please fix your mistakes"` suffix causes the LLM to change arguments on server errors

---

## Trace-by-Trace Breakdown

### Trace 1 — Verbose Retry (2 retry cycles, 82.3s, 6,027 tokens)

| Property | Value |
|---|---|
| Duration | 82.3s |
| Status | `success` (graph-level) |
| LLM calls | 4 |
| Tool calls | 3 (sequential, 1 per cycle) |
| Tool errors | 3 |
| Retries | 2 |
| Direct children | 8 (flow_router → assistant → tools → assistant → tools → assistant → tools → assistant) |
| Total tokens | 6,027 (prompt: 5,823 / completion: 204) |

**Execution Flow:**

```
LLM Call 1 → query_findings(include_execution_overview=true)
  → TOOL ERROR: MCPToolError + "Please fix your mistakes."

LLM Call 2 → query_findings(include_execution_overview=true)       ← RETRY 1: identical args
  → TOOL ERROR: MCPToolError + "Please fix your mistakes."

LLM Call 3 → query_findings(view_mode="distribution", group_by="severity")  ← RETRY 2: different args
  → TOOL ERROR: MCPToolError + "Please fix your mistakes."

LLM Call 4 → Final response (finish_reason=stop)
```

**User-facing response:**
> I attempted to query the latest assessment results, but the **findings service** returned an **internal server error** on each request. Because of that, I could not retrieve:
>
> - Latest execution overview
> - Severity distribution
> - Asset impact summaries
> - Rule violation summaries
>
> ### Result
> No findings data could be retrieved due to a tool execution error.
>
> ### Next Step
> Please retry the request in a moment. If the issue persists, the **findings service** backing the assessment queries may be temporarily unavailable. Once it responds successfully, I can provide:
> - Latest **assessment execution summary**
> - **Severity distribution**
> - **Top impacted assets**
> - **Most violated rules**.

**Per-LLM-call token breakdown:**

| LLM Call | Prompt | Completion | Cached | Reasoning | Action |
|---|---|---|---|---|---|
| 1 | 1,374 | 22 | 1,152 (84%) | 0 | 1 tool call |
| 2 | 1,428 | 22 | 1,152 (81%) | 0 | 1 tool call (retry 1) |
| 3 | 1,482 | 25 | 1,280 (86%) | 0 | 1 tool call (retry 2, different args) |
| 4 | 1,539 | 135 | 1,280 (83%) | 0 | Final response |
| **Total** | **5,823** | **204** | | | |

---

### Trace 2 — Generic One-Liner (0 retries, 18.9s, 1,709 tokens)

| Property | Value |
|---|---|
| Duration | 18.9s |
| Status | `success` (graph-level) |
| LLM calls | 2 |
| Tool calls | 4 (parallel, all in 1 batch) |
| Tool errors | 4 |
| Retries | 0 |
| Direct children | 4 (flow_router → assistant → tools → assistant) |
| Total tokens | 1,709 (prompt: 1,373 / completion: 336) |

**Execution Flow:**

```
LLM Call 1 → 4 parallel tool calls:
  query_findings(include_execution_overview=true)
  query_findings(view_mode="distribution", group_by="severity", metrics=["count"])
  query_findings(view_mode="aggregate", group_by="asset_key", limit=5)
  query_findings(view_mode="aggregate", group_by="rule", limit=5)
  → ALL 4 TOOL ERRORS: MCPToolError + "Please fix your mistakes."

LLM Call 2 → Final response (finish_reason=N/A, no response_metadata)
```

**User-facing response:**
> I'm sorry, but I wasn't able to process your request due to a service error. Please try again in a moment.

**Per-LLM-call token breakdown:**

| LLM Call | Prompt | Completion | Cached | Reasoning | Action |
|---|---|---|---|---|---|
| 1 | 1,373 | 336 | 1,152 (84%) | 64 | 4 parallel tool calls |
| 2 | ? | ? | ? | ? | Final response (no metadata) |
| **Total** | **1,373** | **336** | | | |

---

### Trace 3 — Structured Status, 1 Retry (1 retry cycle, 29.1s, 4,660 tokens)

| Property | Value |
|---|---|
| Duration | 29.1s |
| Status | `success` (graph-level) |
| LLM calls | 3 |
| Tool calls | 3 (2 parallel + 1 retry) |
| Tool errors | 3 |
| Retries | 1 |
| Direct children | 6 (flow_router → assistant → tools → assistant → tools → assistant) |
| Total tokens | 4,660 (prompt: 4,426 / completion: 234) |

**Execution Flow:**

```
LLM Call 1 → 2 parallel tool calls:
  query_findings(include_execution_overview=true)
  query_findings(view_mode="distribution", group_by="severity", metrics=["count"])
  → BOTH TOOL ERRORS: MCPToolError + "Please fix your mistakes."

LLM Call 2 → query_findings(include_execution_overview=true)       ← RETRY 1: simpler query
  → TOOL ERROR: MCPToolError + "Please fix your mistakes."

LLM Call 3 → Final response (finish_reason=stop)
```

**User-facing response:**
> I attempted to retrieve the latest assessment overview, but the findings service returned an internal server error and no data was returned.
>
> ## Status
> - **Execution overview:** Not available (tool error)
> - **Findings data:** Not available (tool error)
>
> Because the tool did not return results, I cannot produce a summary, severity distribution, or impacted assets at this time.
>
> Please try the request again. If the issue persists, the findings service for the latest execution may currently be unavailable.

**Per-LLM-call token breakdown:**

| LLM Call | Prompt | Completion | Cached | Reasoning | Action |
|---|---|---|---|---|---|
| 1 | 1,374 | 111 | 1,152 (84%) | 0 | 2 parallel tool calls |
| 2 | 1,499 | 22 | 1,152 (77%) | 0 | 1 tool call (retry) |
| 3 | 1,553 | 101 | 1,280 (82%) | 0 | Final response |
| **Total** | **4,426** | **234** | | | |

---

## Cross-Trace Comparison

### Behaviour Divergence

| Aspect | Trace 1 | Trace 2 | Trace 3 |
|---|---|---|---|
| Initial tool calls | 1 sequential | 4 parallel | 2 parallel |
| Retry cycles | 2 | 0 | 1 |
| Total LLM calls | 4 | 2 | 3 |
| Total tool calls | 3 | 4 | 3 |
| Duration | 82.3s | 18.9s | 29.1s |
| Total tokens | 6,027 | 1,709 | 4,660 |
| Response length | 154 words | 18 words | 68 words |
| Mentions "findings service" | Yes | No | Yes |
| Mentions "tool error" | Yes | No | Yes |
| Mentions "internal server error" | Yes | No | Yes |
| Uses markdown headers | Yes (`### Result`, `### Next Step`) | No | Yes (`## Status`) |
| Response structure | Bullet list + sections | Single sentence | Status table + explanation |
| Reasoning tokens | 0 | 64 | 0 |

### Response Categorization

| Category | Trace 1 | Trace 2 | Trace 3 |
|---|---|---|---|
| **Tone** | Technical/diagnostic | Apologetic/generic | Clinical/structured |
| **Detail level** | High — lists what couldn't be retrieved, promises what would be shown | Minimal — no specifics | Medium — status table, names what's unavailable |
| **Internal leakage** | High — names service, describes error type, lists architecture components | None | High — names service, exposes "tool error" terminology |
| **Actionability** | Moderate — says to retry, explains what to expect on success | Low — just "try again" | Moderate — says to retry, notes service may be unavailable |

### Token Efficiency

| Metric | Trace 1 | Trace 2 | Trace 3 |
|---|---|---|---|
| Tokens per retry cycle | 2,014 | N/A (no retries) | 1,521 |
| Token cost of retries | 4,488 (74% of total) | 0 | 3,021 (65% of total) |
| Response tokens | 135 | ~30 (no metadata) | 101 |
| Cache hit rate | 81–86% | 84% | 77–84% |
| Cost relative to Trace 2 | **3.5x** | **1.0x** (baseline) | **2.7x** |

---

## Problem Analysis

### Problem 1: Non-Deterministic Error Responses (High Severity)

Despite `temperature: 0.0`, the three responses are radically different:

- **Trace 1:** 154-word structured diagnostic with markdown headers, lists of what failed, and a description of what success would look like
- **Trace 2:** 18-word one-liner apology with no specifics
- **Trace 3:** 68-word structured status with bullet points

**Root cause:** The LLM receives different conversation histories (because retry counts differ) and generates non-deterministic text. Even at temperature 0.0, the different number of prior messages in context produces different completions. Additionally, the initial tool call strategy differs (1 vs 2 vs 4 parallel calls), which means even the first LLM call is non-deterministic.

**Impact:** Users encountering the same failure see wildly different messages. This erodes trust — some users get a helpful diagnostic, others get a dismissive one-liner.

### Problem 2: Non-Deterministic Retry Behaviour (High Severity)

| Retry Pattern | Trace 1 | Trace 2 | Trace 3 |
|---|---|---|---|
| After first batch of errors | Retries with same args | Gives up | Retries with reduced scope |
| After second batch | Retries with different args | — | Gives up |
| After third batch | Gives up | — | — |
| Total wasted tokens | 4,488 | 0 | 3,021 |
| Total wasted time | ~75s | 0s | ~17s |

**Root cause:** Retry is LLM-decided, not graph-coded. The LLM's decision to retry depends on:
- How many errors it sees at once (4 errors → give up; 1 error → retry)
- The `"Please fix your mistakes"` suffix, which misleads the LLM into thinking argument changes might help
- Stochastic generation even at temperature 0 (different prompt layouts cause different behaviour)

**Impact:** Identical failures cost 1,709 tokens (Trace 2) or 6,027 tokens (Trace 1) — a **3.5x cost variance**. Duration ranges from 18.9s to 82.3s — a **4.4x latency variance**.

### Problem 3: Non-Deterministic Initial Strategy (Medium Severity)

The LLM's first tool call differs across all three traces:

| Trace | First LLM call | Tool calls issued |
|---|---|---|
| Trace 1 | 1 sequential call | `query_findings(include_execution_overview=true)` |
| Trace 2 | 4 parallel calls | 4 different `query_findings` queries |
| Trace 3 | 2 parallel calls | `query_findings(include_execution_overview=true)` + `query_findings(distribution)` |

**Root cause:** The LLM decides its query strategy based on the system prompt and user input, but the decision is non-deterministic. Trace 2 used 64 reasoning tokens (others used 0), suggesting Chain-of-Thought was activated inconsistently, which led to the more aggressive 4-call strategy.

**Impact:** The initial strategy affects everything downstream — it determines the error pattern, which determines the retry pattern, which determines the response.

### Problem 4: Internal Architecture Leakage (High Severity)

Two of three responses expose internal details:

| Leaked Detail | Trace 1 | Trace 2 | Trace 3 |
|---|---|---|---|
| "findings service" | Yes | No | Yes |
| "internal server error" | Yes | No | Yes |
| "tool error" / "tool execution error" | Yes | No | Yes |
| "assessment queries" | Yes | No | No |
| "findings service backing the assessment queries" | Yes | No | No |

**Root cause:** The system prompt does not instruct the AI to sanitize error responses. When the LLM retries and accumulates more context about the failure, it becomes more verbose and exposes more internals. Trace 2 (no retries) produced a clean response; Traces 1 and 3 (with retries) leaked architecture.

**Correlation:** More retries → more leaked detail. The retry mechanism directly causes the leakage.

### Problem 5: "Please Fix Your Mistakes" Misleads the LLM (Medium Severity)

The error suffix causes observable behaviour changes:

- **Trace 1, LLM Call 3:** After 2 identical `include_execution_overview` failures, the LLM changes to `view_mode="distribution"` — trying to "fix" arguments that were never wrong
- **Trace 3, LLM Call 2:** After 2 parallel failures, the LLM retries with only the simpler query — reducing scope as if the complex args were the problem

In both cases, the LLM interpreted `"Please fix your mistakes"` as an instruction to change its tool arguments. But the error is a **server-side outage** — no argument change can fix it.

**Impact:** Wasted LLM calls and tokens on mutations that cannot succeed. Trace 1 burned 3 calls and 70+ seconds on pointless retries.

---

## Graph Status Inconsistency

All three traces report `status: success` and `error: null` at the graph level, despite the user receiving an error message in every case. The graph considers the run "successful" because:
1. The agent responded (even though the response describes a failure)
2. No unhandled exception was raised
3. The flow completed all graph nodes

This means monitoring/alerting based on `status` will miss 100% of these failures.

---

## Recommendations

### 1. Implement Deterministic Error Handling at the Graph Level (Critical)

Replace LLM-generated error messages with a graph-level error handler that produces a deterministic, sanitized response:

```python
# In the graph's response node or error handler
def handle_tool_failures(state):
    tool_errors = [m for m in state.messages if m.type == "tool" and m.status == "error"]
    if tool_errors:
        return {
            "messages": [AIMessage(content=(
                "I'm unable to retrieve your assessment data right now. "
                "Please try again in a few minutes. If the problem persists, "
                "contact support."
            ))]
        }
```

This eliminates response variance, prevents internal leakage, and reduces token waste to zero.

### 2. Implement Graph-Level Retry with Backoff (Critical)

Move retry logic from LLM decision-making to the graph:

```python
@retry(max_attempts=2, retry_on=MCPToolError, backoff=exponential(base=2))
async def call_tool(tool_name, args):
    return await mcp_client.call(tool_name, args)
```

This ensures:
- Consistent retry count (always 0, 1, or 2 — not LLM-decided)
- Proper backoff (not instant retries)
- No argument mutation on server errors

### 3. Differentiate Server Errors from Client Errors in Tool Error Messages (High)

Replace the blanket `"Please fix your mistakes"` suffix with error-appropriate guidance:

```python
if isinstance(error, MCPToolError) and is_server_error(error):
    return f"Tool temporarily unavailable (server error). Do not retry or modify arguments."
else:
    return f"Invalid tool arguments: {error.message}. Please fix your mistakes."
```

This prevents the LLM from wasting tokens mutating arguments on server errors.

### 4. Add System Prompt Error Handling Guardrails (High)

Add to the system prompt:

```
## Error Handling
When tool calls fail:
- NEVER mention internal service names, tool names, or error types to the user
- Respond with a brief, user-friendly message: "I'm unable to retrieve that data right now. Please try again."
- Do not describe what you attempted to do or what failed internally
- Do not use markdown headers or structured status sections for error responses
- Keep error messages under 30 words
```

### 5. Fix Graph Status to Reflect User-Facing Outcome (Medium)

Update the graph to set `status: error` when the final response describes a failure:

```python
# After generating the final response
if all_tools_failed(state):
    raise GraphError("All tool calls failed — user received error message")
```

This enables monitoring and alerting on actual user-facing failures.

### 6. Constrain Initial Tool Call Strategy (Low)

If the initial query approach should be deterministic (e.g., always start with an execution overview before querying distributions), encode this as a graph-level multi-step plan rather than letting the LLM decide:

```python
# Step 1: Always fetch overview first
overview = await call_tool("query_findings", {"include_execution_overview": True})
# Step 2: Only if overview succeeds, fan out to detail queries
if overview.success:
    await asyncio.gather(
        call_tool("query_findings", {"view_mode": "distribution", ...}),
        call_tool("query_findings", {"view_mode": "aggregate", ...}),
    )
```

---

## Summary of Findings

| Finding | Severity | Category |
|---|---|---|
| Three different error responses for identical failure (temp 0.0) | **Critical** | Consistency |
| Retry count varies 0–2 with 3.5x token cost variance | **Critical** | Reliability / Cost |
| Internal architecture leaked in 2 of 3 responses ("findings service") | **High** | Security / Abstraction |
| Initial tool call strategy varies (1, 2, or 4 parallel) | **Medium** | Consistency |
| "Please fix your mistakes" causes pointless argument mutation | **Medium** | Error Handling |
| Graph reports `status: success` for all 3 user-facing errors | **Medium** | Observability |
| Duration variance 18.9s–82.3s (4.4x) for identical input | **Low** | Performance |
| Reasoning tokens activated inconsistently (64 in Trace 2 only) | **Low** | Cost / Predictability |
