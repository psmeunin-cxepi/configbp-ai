# Error Handling & Resilience Specification

## 1. Objective

All code in the LangGraph agent and MCP server **must** handle errors according to this specification. The goals are:

1. **No internal error details reach the user.** Error messages shown to the user must be fixed, generic strings — never exception text, stack traces, or internal identifiers.
2. **Errors are classified at the source.** Every exception raised by a tool or service must declare both *retryability* (transient or permanent) and *category* (`client_error`, `server_error`, `transient`, `auth_error`). **Programmatic retry** (resending the identical request) is handled by infrastructure layers, not the LLM.
3. **Transient failures are retried automatically.** Each layer retries within its scope before escalating. A single transient failure should not reach the user.
4. **The system recovers from initialization failures.** If a dependency (MCP server, LLM provider) is temporarily unavailable at startup, the system must re-attempt on subsequent requests rather than permanently degrading.

### Programmatic retry vs LLM re-invocation

This spec distinguishes two kinds of "retry":

- **Programmatic retry** — the same tool call with the same arguments is re-sent automatically by infrastructure (tenacity, `awrap_tool_call`, `with_retry()`, `RetryPolicy`). The LLM is not involved and does not see intermediate failures. This is governed by retry budgets (Section 5) and must never be an LLM decision.
- **LLM re-invocation** — the LLM receives a structured error with `category`, `safe_message`, and optionally `hint`. Based on its Tool Failure Handling Policy (Section 4.4), it decides the next action. This is an LLM reasoning action governed by system prompt instructions, not a programmatic retry — the payload and intent may differ.

---

## 2. Architecture Overview

### 2.1. Error Propagation Path

```
User request
  → LangGraph (graph execution)
    → Assistant node (LLM invocation)
      → ToolNode (tool call dispatch)
        → MCP Client (network transport)
          → MCP Server (error handling middleware)
            → Tool function
              → Database / external service
```

Errors travel back up this stack. Each layer has a defined responsibility — it **must not** silently swallow errors, and it **must not** pass raw internal details upward.

### 2.2. Layered Error Strategy

| Layer | Scope | Location | Responsibility |
|-------|-------|----------|----------------|
| **1 — Tool Execution** | Tool functions, DB/service queries | MCP server — service layer | Raise typed exceptions. Retry transient errors locally |
| **2 — MCP Server** | Exception hierarchy, middleware | MCP server — models, middleware | Classify exceptions (transient vs permanent). Sanitize before MCP response |
| **3 — ToolNode / MCP Client** | Agent-side tool handling | Agent — service layer | Sanitize error text before the LLM sees it. Optionally retry retryable tool failures. Propagate tool loading exceptions |
| **4 — Agent & Graph** | LLM invocation, graph execution | Agent — nodes, core, services | Retry transient LLM errors. Compose fallback providers. Recover from initialization failures. Graph-level retry safety net |

Errors recovered at a lower layer (via successful retry) do not propagate further. Errors that exhaust retries are classified and escalated upward in structured form. Each layer trusts that layers below it have already retried within their scope.

---

## 3. Section A — Tool Error Propagation Through MCP

This section covers Layers 1–3: how tool errors originate, are classified, and are presented to the LLM.

### 3.1. Layer 1 — Tool Execution

**Scope:** Tool function bodies and database/service calls.

#### Rules

1. **Never return error strings.** Tool functions must **raise** an exception on failure, not return a string containing error details. Returning an error string bypasses all downstream error handling — the MCP response appears successful and the LLM receives raw error text.

   ```python
   # ✗ WRONG — swallows the exception, bypasses middleware
   except Exception as e:
       return f"Error retrieving data: {str(e)}"

   # ✓ CORRECT — exception flows through ErrorHandlingMiddleware
   except Exception as e:
       logger.error("Error retrieving data: %s", e)
       raise ToolExecutionException("Unable to retrieve the requested data.")
   ```

2. **Use the most specific exception subclass.** Choose the exception type that matches the failure mode:

   | Failure mode | Exception class | Category | Retryable? |
   |---|---|---|---|
   | Bad user input, missing parameters | `ToolValidationException` | `client_error` | No |
   | Auth / permission failure | `ToolAuthorizationException` | `auth_error` | No |
   | Query/connection timeout | `ToolTimeoutException` | `transient` | Yes |
   | Network / DB connection error | `ToolConnectionException` | `transient` | Yes |
   | All other errors | `ToolExecutionException` | `server_error` | No |

3. **Use safe messages in exceptions.** The message passed to the exception constructor may eventually reach the LLM (after middleware processing). It must not contain internal identifiers, table names, query text, or stack traces.

   ```python
   # ✗ WRONG — leaks internals
   raise ToolExecutionException(f"SELECT failed on iq_findings: {e}")

   # ✓ CORRECT — safe for downstream consumption
   raise ToolExecutionException("Unable to retrieve assessment findings.")
   ```

4. **Retry transient infrastructure errors locally.** Database queries and external HTTP calls should use `tenacity` retry decorators for transient errors (timeouts, connection resets). This is the fastest retry path — no MCP round-trip overhead.

   ```python
   @retry(
       retry=retry_if_exception_type((ConnectionError, OperationalError)),
       stop=stop_after_attempt(3),
       wait=wait_exponential_jitter(initial=1, max=10),
       reraise=True,
   )
   async def execute_query(self, query, params):
       ...
   ```

   After local retries are exhausted, raise the appropriate `ToolException` subclass and let it propagate.

### 3.2. Layer 2 — MCP Server Error Classification

**Scope:** Exception hierarchy and `ErrorHandlingMiddleware`.

#### Rules

1. **Every `ToolException` subclass must declare `retryable` and `category`.** The base `ToolException` defaults to `retryable=False`. Subclasses for transient failures set `retryable=True`. Each subclass has a `category` that tells the LLM *why* it failed:

   ```
   ToolException (retryable=False)
     ├── ToolValidationException     category="client_error"   retryable=False
     ├── ToolAuthorizationException  category="auth_error"      retryable=False
     ├── ToolExecutionException      category="server_error"    retryable=False
     ├── ToolTimeoutException        category="transient"       retryable=True
     └── ToolConnectionException     category="transient"       retryable=True
   ```

   **Why categories matter for the LLM:**

   | Category | LLM should... | Example |
   |---|---|---|
   | `client_error` | Self-correct arguments and re-invoke with corrected args | Bad date format, missing required field |
   | `server_error` | Pivot to a different tool or inform the user | Internal server failure after retries exhausted |
   | `transient` | Do **not** retry — infrastructure already retried. Inform the user or suggest trying later | Rate limit, temporary DB overload |
   | `auth_error` | Stop retrying, inform the user | Permission denied, auth failure |

   Without this classification, the LLM cannot distinguish "fix your arguments" from "the server is down" — leading to blind retry loops that waste tokens and hit rate limits.

2. **Encode errors as structured JSON in the MCP error response.** The `ErrorHandlingMiddleware` must produce a JSON object (not a bare string) so the LLM can parse the error category deterministically:

   ```python
   import json

   error_payload = json.dumps({
       "status": "error",
       "error_code": exc.code,
       "category": exc.category,
       "is_transient": exc.retryable,
       "safe_message": exc.message,
   })
   raise FastMCPToolError(error_payload) from exc
   ```

   For `client_error` category, include a `hint` field when the exception message explains what the LLM should fix:

   ```python
   # ToolValidationException with actionable hint
   error_payload = json.dumps({
       "status": "error",
       "error_code": "INVALID_ARGUMENT",
       "category": "client_error",
       "is_transient": False,
       "safe_message": "The 'date_range' must be in ISO 8601 format (YYYY-MM-DD).",
       "hint": "Convert the relative date to a specific date string before calling again.",
   })
   ```

3. **Sanitize all exceptions in middleware.** No exception — whether `ToolException`, unexpected `RuntimeError`, or anything else — may pass through `ErrorHandlingMiddleware` with raw internal details. Unclassified exceptions must produce a generic `server_error` JSON payload:

   ```python
   # Fallback for unexpected exceptions
   error_payload = json.dumps({
       "status": "error",
       "error_code": "INTERNAL_ERROR",
       "category": "server_error",
       "is_transient": False,
       "safe_message": "An unexpected error occurred.",
   })
   ```

4. **Distinguish LLM-visible from user-visible fields.** The structured error envelope contains fields with different visibility scopes:

   | Field | Audience | Purpose |
   |---|---|---|
   | `safe_message` | LLM **and** user | Contains no internal details and is safe to show the user if the LLM chooses to, per the user-response policy below. Not necessarily forwarded verbatim — the LLM may rephrase or omit it |
   | `hint` | LLM only | Actionable guidance for the LLM to self-correct. May reference parameter names or formats. Must not be forwarded to the user |
   | `error_code` | LLM only | Machine-readable code for programmatic logic |
   | `category` | LLM only | Determines the LLM's next action (see table above) |
   | `is_transient` | Infrastructure only | Drives programmatic retry at Layer 3; the LLM should not act on this field directly |

   **User-response policy by category:**

   | Category | User should see... |
   |---|---|
   | `client_error` | Nothing (LLM silently corrects and re-invokes), or the `safe_message` if the LLM cannot self-correct |
   | `server_error` | A generic apology: *"I'm unable to retrieve that information right now."* |
   | `transient` | Nothing if Layer 3 retried successfully; otherwise same as `server_error` |
   | `auth_error` | *"You don't have permission to access that information."* or similar from `safe_message` |

### 3.3. Layer 3 — ToolNode / MCP Client (Agent Side)

**Scope:** `ToolNode` configuration, MCP client tool loading.

#### Rules

1. **The LLM must never see raw error text from tools.** Errors that went through Layer 2 are already structured JSON — the `ToolNode` passes these through to the LLM as-is. However, some errors bypass Layer 2 entirely (e.g., MCP client transport failures, connection timeouts before reaching the server). For these unclassified errors, the `ToolNode` middleware must produce a structured JSON fallback:

   ```json
   {
     "status": "error",
     "error_code": "TOOL_CALL_FAILED",
     "category": "server_error",
     "is_transient": false,
     "safe_message": "This tool call failed due to an unexpected issue."
   }
   ```

   **Transport parsing contract:** The `ToolNode` middleware must determine whether an error is already structured:
   1. Attempt to parse the error content as JSON.
   2. If valid JSON **and** contains `status == "error"`, a `category` field, **and** a `safe_message` field → treat as a Layer 2 structured error, pass through.
   3. If not valid JSON, or missing any of those required fields → treat as unclassified, produce the generic fallback envelope above.

   This ensures malformed errors, transport wrapper text, or raw exception strings never reach the LLM.

   The `safe_message` field must be factual, not instructive — the LLM decides the next action based on `category`:
   - `client_error` → self-correct arguments and re-invoke with corrected args (LLM re-invocation, not programmatic retry)
   - `transient` → the LLM must not retry (infrastructure may already have retried within its scope); inform the user or suggest trying later
   - `server_error` → try a different tool or inform the user
   - `auth_error` → stop retrying, inform the user

2. **Optionally retry `transient` errors at the ToolNode level.** If using `awrap_tool_call` middleware, detect `"is_transient": true` in the structured error and retry the tool call (up to a bounded limit) before returning the error to the LLM. Do **not** retry `client_error` — the LLM needs to see the error to fix its arguments.

   > ⚠️ **Double-retry awareness:** If Layer 1 already retries (e.g., tenacity on Trino), a Layer 3 retry on the same failure path compounds attempts. Design retry counts so the total across layers stays within acceptable latency. See the implementation plan for mitigation options.

3. **Propagate tool loading exceptions.** `list_tools()` and similar initialization calls must **not** catch exceptions and return empty lists. An empty list must mean "the server responded with zero tools," not "the server was unreachable." Callers must be able to distinguish:
   - **Exception raised** → server down → retry with backoff
   - **Empty list returned** → server healthy, no tools registered → cache immediately

4. **Cache tool lists correctly.** Use `is not None` checks so an empty list `[]` is also cached and not re-fetched:

   ```python
   if _cached_tools is not None:  # [] is a valid cached value
       return _cached_tools
   ```

---

## 4. Section B — LLM & Graph Resilience

This section covers Layer 4: LLM invocation retry/fallback, tool loading recovery, graph-level retry, and the system prompt contract for tool failure handling.

### 4.1. LLM Invocation Retry & Fallback

**Scope:** LLM provider calls (assistant node, LLM factory).

#### Rules

1. **Wrap LLM instances with `with_retry()` for transient HTTP errors.** Every LLM created by `llm_factory` should be wrapped to retry on timeouts, connection errors, rate limits (429), and server errors (5xx). Use LangChain's built-in `Runnable.with_retry()` — do not write manual retry loops.

   ```python
   llm = base_llm.with_retry(
       retry_if_exception_type=(httpx.TimeoutException, httpx.ConnectError),
       stop_after_attempt=3,
       wait_exponential_jitter=True,
   )
   ```

2. **Compose fallback providers with `with_fallbacks()`.** If a primary LLM provider fails after retries, fall back to a secondary provider. Use LangChain's `Runnable.with_fallbacks()` — do not write manual try/except fallback code.

   ```python
   llm = primary.with_fallbacks(
       fallbacks=[fallback_provider],
       exceptions_to_handle=(LLMInvocationError,),
   )
   ```

3. **Keep provider-specific auth recovery as custom handlers.** Some providers require token refresh with cache invalidation (e.g., Mistral 401). This is beyond simple retry semantics and may remain as a targeted custom handler.

### 4.2. Tool Loading Recovery

**Scope:** Tool initialization logic in the assistant node.

#### Rules

1. **Graph compilation must not require MCP reachability.** The graph must compile and start successfully even if the MCP server is unavailable. Tool loading and binding must be deferred to request time (lazy initialization), not performed eagerly at graph construction. This ensures the backoff and recovery logic in this section is actually reachable.

2. **Never permanently disable tools after a loading failure.** If the tool loading function fails, the system must re-attempt on subsequent user requests — not wait for a restart.

3. **Use exponential backoff with a cap.** Track the next retry time and double the backoff on each failure, capped at a maximum (e.g., 5 minutes). Reset backoff to the initial value on success.

   | Failure # | Backoff | Cumulative wait |
   |-----------|---------|-----------------|
   | 1 | 5s | 5s |
   | 2 | 10s | 15s |
   | 3 | 20s | 35s |
   | 4 | 40s | 75s |
   | 5 | 80s | 155s |
   | 6+ | 300s (cap) | +5 min each |

4. **Between backoff windows, operate without tools.** While waiting, the assistant operates in chat-only mode (no tool binding). This is degraded but not broken — the user still gets LLM responses.

### 4.3. Graph-Level RetryPolicy

**Scope:** `StateGraph.add_node()` configuration.

#### Rules

1. **Apply `RetryPolicy` to nodes that make external calls.** The `assistant` node (LLM calls) and `tools` node (MCP calls) should have a `RetryPolicy` as a safety net for transient errors that survive lower layers.

   ```python
   graph.add_node("assistant", assistant, retry=RetryPolicy(
       max_attempts=3,
       initial_interval=1.0,
       backoff_factor=2.0,
       retry_on=_is_transient_error,
   ))
   ```

2. **Use a predicate to limit retry scope.** Only retry on transient infrastructure exceptions (e.g., `ConnectionError`, `TimeoutError`, MCP transport errors). Do not retry application-logic errors, validation errors, or LLM content issues.

3. **Do not apply retry to deterministic nodes.** Nodes that perform no external calls and cannot fail transiently (e.g., routing nodes) should not have a `RetryPolicy`.

4. **Apply retry to subgraph nodes that depend on external services.** Any subgraph node that calls a database or external API benefits from retry.

### 4.4. Tool Failure Handling Policy (System Prompt)

**Scope:** System prompt instructions that govern LLM behavior when a tool call returns a structured error.

Sections 4.1–4.3 are programmatic — they handle errors in infrastructure code before the LLM ever sees them. When programmatic handling is exhausted, the structured error envelope (from Layers 1–3) reaches the LLM as a `ToolMessage`. What the LLM does next is governed by its **system prompt**, not by code. Without explicit instructions, the LLM may ignore the error category, fabricate results, or enter blind retry loops.

This section defines the **minimum required** failure-handling instructions that must be present in the system prompt. These are a subset of the broader Tool Use Policy (see prompt-auditor skill, Section 5: "Tool Use Policy"). Only the error-handling rules are specified here.

#### Required system prompt instructions

The system prompt **must** include instructions that cover all of the following behaviors:

1. **Parse structured errors.** When a tool returns a JSON error with `category`, `safe_message`, and optionally `hint`, the LLM must use these fields to determine its next action — not guess from the raw text.

2. **Act on error category.** The system prompt must map each category to expected LLM behavior:

   | Category | Required LLM behavior |
   |---|---|
   | `client_error` | Read the `hint` field. Correct the arguments and re-invoke the tool with a fixed payload. If self-correction is not possible, inform the user using `safe_message` |
   | `transient` | Do **not** retry the same call (infrastructure already retried). Inform the user that the service is temporarily unavailable or suggest trying again later |
   | `server_error` | Do **not** retry. Inform the user the request could not be completed. If an alternative tool could fulfill the same intent, the LLM may try it |
   | `auth_error` | Do **not** retry. Inform the user they lack permission, using `safe_message` |

3. **Never fabricate tool results.** If a tool call fails, the LLM must **not** invent data, pretend the call succeeded, or generate plausible-looking results. It must either correct and re-invoke (for `client_error`) or inform the user of the failure.

4. **Never expose `hint` or `error_code` to the user.** The `hint` field is LLM-only context for self-correction. The LLM may use `safe_message` in its response to the user but must not forward `hint`, `error_code`, or `is_transient` values.

5. **Limit self-correction attempts.** For `client_error`, the LLM should attempt self-correction at most once. If the second attempt also fails, inform the user rather than entering a correction loop.

#### Relationship to Tool Use Policy

These rules correspond to the **Failure Handling** subsection of the Tool Use Policy (prompt-auditor skill, Section 5). The broader policy also covers:
- **Use Criteria** — when to use a tool vs answer directly
- **Priority & Sequencing** — which tools to prefer
- **Confirmation Requirements** — which actions need user approval
- **Tool Boundaries** — required, optional, restricted, or prohibited tools
- **Non-Fabrication Rule** — general prohibition on inventing outputs

This spec only mandates the failure-handling subset. The full Tool Use Policy should be implemented as part of the system prompt design but is outside the scope of this error-handling specification.

---

## 5. Error Budget & Retry Ownership

When multiple layers retry the same failure path, the total attempts compound. Each failure path must have a **primary retry owner** — other layers act as safety nets with minimal attempts (1 = catch only, no retry).

### 5.1. Default Retry Ownership

| Failure path | Primary retry layer | Max attempts | Secondary layer | Max attempts | Notes |
|---|---|---|---|---|---|
| DB/service transient error (timeout, connection) | **L1** (tenacity) | 3 | L4.3 (RetryPolicy) | 1 (safety net) | L3 does **not** retry — avoids compounding with L1 |
| MCP transport failure (connection to MCP server) | **L3** (ToolNode middleware) | 2 | L4.3 (RetryPolicy) | 1 (safety net) | L1 not involved (error is between agent and MCP server) |
| LLM HTTP error (timeout, 429, 5xx) | **L4.1** (`with_retry`) | 3 | L4.3 (RetryPolicy) | 1 (safety net) | Provider-level retry before fallback |
| LLM provider down (all retries exhausted) | **L4.1** (`with_fallbacks`) | 1 per fallback | — | — | Switch to secondary provider |
| Tool loading failure (MCP server unavailable) | **L4.2** (backoff) | ∞ (with backoff) | — | — | Re-attempt on subsequent requests |
| Client error (bad arguments) | **None** (not retried) | 0 | — | — | Returned to LLM for self-correction (re-invocation, not retry) |
| Auth error (permission denied) | **None** (not retried) | 0 | — | — | Returned to LLM to inform user |

### 5.2. Worst-Case Timing

| Path | Layers involved | Max total attempts | Example timing |
|------|----------------|-------------------|---------------|
| DB transient error | L1 (3) × L4.3 (1) | 3 | ~30s worst case |
| MCP transport failure | L3 (2) × L4.3 (1) | 2 | ~6s worst case |
| LLM HTTP timeout | L4.1 (3) × L4.3 (1) | 3 | ~15s worst case |
| LLM provider failure + fallback | L4.1 (3) + fallback L4.1 (3) | 6 | ~30s worst case |

**Rule:** Secondary layers default to `max_attempts=1` (execute once, no retry — the node runs but is not retried on failure). Increase only when justified by observed failure patterns and acceptable latency.

---

## 6. Open Questions

### OQ-1: SQL syntax errors — client_error or server_error?

If the LLM generates a SQL query and passes it to a tool, a **SQL syntax error** from the database (e.g., Trino's `PrestoUserError`) is arguably a `client_error` — the LLM constructed a bad query and could fix it on retry. However:

- **What does the DB actually return?** Trino raises `trino.exceptions.TrinoUserError` for syntax errors vs `OperationalError` for infrastructure failures. Other databases may differ.
- **How is this captured on the tool side?** If the tool service catches all exceptions uniformly, it cannot classify SQL syntax errors as `client_error`. To do so, the tool would need to catch DB-specific syntax error types separately and include the relevant error message (e.g., `"Syntax error at line 3: unexpected 'GROUPP'"`) in a `ToolValidationException` with a `hint`.
- **Security tension:** Passing DB error messages back to the LLM gives it information to self-correct, but may leak schema details (table names, column names) in the error text. This conflicts with Rule 3.1.3 ("use safe messages").
- **Does this apply to our tools?** If tools accept pre-built queries from the LLM (text-to-SQL), the LLM needs syntax feedback. If tools only accept structured parameters (hostname, date range) and build SQL internally, syntax errors are always `server_error` (a bug in the tool, not the LLM's fault).

**Decision needed:** Define which tools accept LLM-constructed queries vs structured parameters, and whether DB syntax error messages can be safely relayed to the LLM (possibly sanitized to remove schema details).

### OQ-2: Prompt loading resilience

The spec covers tool loading failures (Section 4.2) but not system prompt loading. If the system prompt is fetched from an external source (MCP tool, database, API) at request time, it has similar failure modes: the source may be unavailable, the response may be empty, or the fetch may time out.

- **Should prompt loading failures follow the same backoff model as tool loading?** Or is a hardcoded fallback prompt sufficient?
- **What is the blast radius?** A missing system prompt may cause the LLM to behave unpredictably — arguably worse than missing tools (which simply reduces capability).
- **Is a fallback prompt always acceptable?** In some architectures, the prompt encodes per-tenant or per-session context that cannot be substituted with a generic fallback.

**Decision needed:** Define whether prompt loading is in scope for this spec, and if so, what the recovery policy is (backoff + retry, static fallback, or fail-fast).

---

## 7. Quick Reference — What NOT To Do

| Anti-pattern | Why it's wrong | Correct approach |
|---|---|---|
| `except Exception: return f"Error: {e}"` | Bypasses all error handling layers | `raise ToolExecutionException("safe message")` |
| `except Exception: return []` | Hides server failures from callers | Let exception propagate; return `[]` only on success |
| Logging `str(e)` in error messages sent to user | Internal details leak | Use fixed generic messages; log details server-side only |
| Same generic error message for all failure types | LLM can't distinguish "fix your args" from "server down" — blind retry loops | Structured JSON with `category` field (`client_error`, `transient`, `server_error`, `auth_error`) |
| LLM blindly retries a failed tool call with identical arguments | Non-deterministic, wastes tokens, compounds retries already done by infrastructure | Classify at source; retry programmatically based on `is_transient`. LLM may re-invoke with *corrected* args for `client_error` only |
| Manual try/except retry loops for LLM calls | Verbose, error-prone, non-composable | `with_retry()` + `with_fallbacks()` |
| No `RetryPolicy` on nodes with external calls | Single transient failure crashes the graph | Add `RetryPolicy` with transient-error predicate |
| Permanently disabling tools after load failure | One bad startup = degraded for entire session | Backoff + re-attempt on subsequent requests |

---

## 8. Implementation Plans

For detailed code examples, proposed changes, and phased implementation steps, see:

- [PLAN_tool_error_handling.md](PLAN_tool_error_handling.md) — Layers 1–3 implementation (tool execution, MCP server, ToolNode/MCP client)
- [PLAN_llm_graph_resilience.md](PLAN_llm_graph_resilience.md) — Layer 4 implementation (LLM retry/fallback, tool loading recovery, graph RetryPolicy)
