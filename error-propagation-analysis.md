# Error Handling Analysis: Inconsistent Error Propagation in Graph Execution

**Date:** 2026-03-30  
**Traces Analysed:**
| Label | Trace URL | Trace ID |
|---|---|---|
| Trace 1 — Generic service error | [LangSmith](https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/042673d8-68f0-494f-8680-7b08dbc7c2e7/r) | `042673d8-68f0-494f-8680-7b08dbc7c2e7` |
| Trace 2 — Detailed internal error | [LangSmith](https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/0c08bf7e-f751-485a-955d-3705e8568318/r) | `0c08bf7e-f751-485a-955d-3705e8568318` |

**Revision:** `v1.0.58-4-g884fe85`  
**Model:** `gpt-5.3-chat-2026-03-03` (temperature 0.0, max_tokens 2000)  
**Agent:** Configuration Agent (assessments-configuration-summary)

---

## Executive Summary

Both traces originate from the same user request ("Show me a summary of my assessment results") and fail due to identical `MCPToolError` server-side errors from the `query_findings` tool. However, the agent produces **two fundamentally different error responses**, and the **retry strategies differ** between runs. This reveals three distinct problems:

1. **Inconsistent error response format** — the LLM decides the error text, so the user may see internal details or a vague message depending on the model's mood.
2. **Internal implementation details exposed to the user** — one response names the "findings service" and describes "internal server error", leaking architecture.
3. **Non-deterministic retry logic** — the same error condition triggers different retry patterns (0 retries vs 1 retry), indicating the retry mechanism is not codified.

---

## Trace-by-Trace Breakdown

### Trace 1 — Generic Service Error (No Retry)

| Property | Value |
|---|---|
| Run type | `chain` (graph-level) |
| Duration | 18.9 s |
| Status | `success` (graph completed, but user got an error message) |
| Total tokens | 1,709 (prompt: 1,373 / completion: 336) |
| LLM calls | 2 |

**Execution Flow:**

```
Step 1: LLM Call #1
  → AI requests 4 parallel tool calls:
      query_findings(include_execution_overview=true)
      query_findings(view_mode="distribution", group_by="severity")
      query_findings(view_mode="aggregate", group_by="asset_key", limit=5)
      query_findings(view_mode="aggregate", group_by="rule", limit=5)

Step 2: Tool Execution
  → All 4 calls return: MCPToolError('An internal server error occurred while executing the tool.')
  → Each is appended with: "Please fix your mistakes."

Step 3: LLM Call #2
  → AI sees 4 errors, gives up immediately
  → Responds: "I'm sorry, but I wasn't able to process your request due to a service error.
               Please try again in a moment."
  → No retry attempted
```

**User-facing response:**
> I'm sorry, but I wasn't able to process your request due to a service error. Please try again in a moment.

**Assessment:** This response is generic but safe — it does not expose internals. However, it provides zero diagnostic value to the user.

---

### Trace 2 — Detailed Internal Error (1 Retry)

| Property | Value |
|---|---|
| Run type | `llm` (this trace captures a single LLM call within the graph at step 6) |
| Duration | 4.4 s |
| Status | `success` |
| Total tokens | 1,654 (prompt: 1,553 / completion: 101) |
| LangGraph step | 6 (node: `assistant`) |

**Execution Flow (reconstructed from input messages):**

```
Step 1: LLM Call #1 (not in this trace, earlier in graph)
  → AI requests 2 parallel tool calls:
      query_findings(include_execution_overview=true)
      query_findings(view_mode="distribution", group_by="severity")

Step 2: Tool Execution
  → Both return MCPToolError + "Please fix your mistakes."

Step 3: LLM Call #2 (retry — also earlier in graph)
  → AI retries with 1 tool call:
      query_findings(include_execution_overview=true)
  → Returns MCPToolError again

Step 4: LLM Call #3 (THIS trace, langgraph_step=6)
  → AI sees 3 cumulative errors, decides to respond to user
  → Responds with detailed internal explanation
```

**User-facing response:**
> I attempted to retrieve the latest assessment overview, but the **findings service** returned an **internal server error** and no data was returned.
> 
> ## Status
> - **Execution overview:** Not available (tool error)
> - **Findings data:** Not available (tool error)
>
> Because the tool did not return results, I cannot produce a summary, severity distribution, or impacted assets at this time.
>
> Please try the request again. If the issue persists, the **findings service for the latest execution** may currently be unavailable.

**Assessment:** This response is more informative but **exposes internal architecture details**:
- Names the "findings service" — a backend component the user should not know about
- Describes "internal server error" — exposes the error classification
- Mentions "tool error" — reveals the agent uses tools

---

## Problem Analysis

### Problem 1: Inconsistent Error Response Format

| Aspect | Trace 1 | Trace 2 |
|---|---|---|
| Error message to user | Generic ("service error") | Detailed (names service, error type) |
| Mentions internal components | No | Yes ("findings service", "tool error") |
| Provides structured status | No | Yes (markdown with headers) |
| Actionable guidance | "try again" | "try again, service may be unavailable" |

**Root cause:** The error response is entirely generated by the LLM on each invocation. There is no structured error handler or response template. The LLM non-deterministically decides how much detail to include based on:
- How many errors it has seen (4 vs 3)
- Whether it retried (more context = more detail in response)
- The model's interpretation of the system prompt's "grounding" instructions

**Impact:** Users see wildly different error messages for the same failure mode, creating a confusing and unreliable experience.

### Problem 2: Internal Details Exposed to Users

Trace 2's response leaks several pieces of internal architecture:

| Leaked Detail | Example Text | Risk |
|---|---|---|
| Backend service name | "findings service" | Reveals microservice architecture |
| Error classification | "internal server error" | Exposes HTTP error semantics |
| Tool mechanism | "tool error", "tool did not return results" | Reveals agent-tool architecture |
| Service dependency | "findings service for the latest execution" | Reveals execution pipeline |

**Root cause:** The system prompt instructs the AI to be transparent about tool failures ("If any query returns no results, state that clearly"), but does not instruct it to **sanitize error details** before responding to the user. The LLM interprets "state that clearly" as permission to describe what happened internally.

**Impact:** Security and abstraction leakage. Users gain knowledge of internal architecture that could be used for social engineering or that simply creates confusion about implementation details.

### Problem 3: Non-Deterministic Retry Behavior

| Aspect | Trace 1 | Trace 2 |
|---|---|---|
| Initial tool calls | 4 parallel | 2 parallel |
| Errors before giving up | 4 (one batch) | 3 (two batches) |
| Retry attempts | 0 | 1 |
| Total LLM calls | 2 | 3 |
| Total tokens consumed | 1,709 | 1,654+ (this trace only shows final LLM call) |

**Root cause:** The retry logic is not implemented as a graph-level mechanism. Instead, the LLM itself decides whether to retry based on the error messages. This means:
- Sometimes it retries (Trace 2: tried once more with a simpler query)
- Sometimes it doesn't (Trace 1: 4 errors felt conclusive, gave up immediately)
- The number of retries is unpredictable and unbounded (could keep retrying)

**Additional concern:** The tool error message includes `"Please fix your mistakes."` — this is **misleading** because the error is a server-side `MCPToolError`, not a client-side argument validation error. This phrase actively steers the LLM toward modifying its tool arguments when the real issue is a backend outage.

---

## Error Message Dissection

The tool error returned to the LLM contains two parts:

```
Error: MCPToolError('An internal server error occurred while executing the tool.')
Please fix your mistakes.
```

| Part | Source | Problem |
|---|---|---|
| `MCPToolError('An internal server error occurred...')` | MCP server / tool wrapper | Appropriate for server errors, but should distinguish 5xx from 4xx |
| `Please fix your mistakes.` | LangGraph/LangChain tool error handler | **Incorrect.** This was a server error, not a client mistake. This anti-pattern causes the LLM to retry with modified arguments instead of recognizing the outage |

The `"Please fix your mistakes"` suffix is the default LangChain `ToolException` handler behavior. It makes sense for validation errors but is harmful for transient server failures.

---

## Recommendations

### 1. Implement Structured Error Responses (High Priority)

Replace LLM-generated error messages with a deterministic error handler at the graph level:

```python
# In the graph error handler or response node
if all_tools_failed(tool_results):
    return {
        "messages": [AIMessage(content=(
            "I'm unable to retrieve your assessment data right now. "
            "Please try again in a few minutes. If the problem persists, "
            "contact support."
        ))]
    }
```

This ensures **every** error scenario produces the same sanitized, user-friendly message regardless of what the LLM would otherwise generate.

### 2. Sanitize Error Messages Passed to the LLM

If the LLM must see errors (for retry decisions), strip internal details:

```python
# Instead of:
"Error: MCPToolError('An internal server error occurred while executing the tool.')\nPlease fix your mistakes."

# Return:
"The tool call failed due to a temporary service issue. Do not retry — respond to the user that the service is temporarily unavailable."
```

### 3. Implement Deterministic Retry Logic

Move retry decisions out of the LLM and into the graph:

```python
# Graph-level retry with exponential backoff
@retry(max_attempts=2, retry_on=MCPToolError, backoff=exponential)
async def call_tool(tool_name, args):
    return await mcp_client.call(tool_name, args)
```

This ensures consistent retry behavior regardless of which LLM call encounters the error.

### 4. Fix the "Please Fix Your Mistakes" Error Suffix

Differentiate between client errors (bad arguments) and server errors (5xx/outage):

```python
# In tool error handler
if isinstance(error, MCPToolError) and error.is_server_error:
    return "Tool unavailable (server error). Do not modify arguments."
else:
    return f"Invalid tool arguments: {error.message}. Please fix your mistakes."
```

### 5. Add System Prompt Guardrails

Add explicit instructions to prevent internal detail leakage:

```
# Error Handling

When tool calls fail:
- Never mention internal service names, tool names, or error codes to the user.
- Respond with a brief, user-friendly message.
- Do not explain the technical reason for the failure.
- Do not structure error responses differently from success responses.
```

---

## Summary of Findings

| Finding | Severity | Category |
|---|---|---|
| LLM generates different error messages for same failure | **High** | Consistency |
| User-facing response exposes "findings service" and "internal server error" | **High** | Security / Abstraction |
| Retry behavior is LLM-decided, not deterministic | **Medium** | Reliability |
| "Please fix your mistakes" misleads LLM on server errors | **Medium** | Error Handling |
| Graph reports `status: success` even when user sees an error | **Low** | Observability |
| No circuit breaker or max-retry cap in graph | **Low** | Reliability |
