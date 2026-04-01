# Trace Analysis: Ambiguity Handling Gap

## Metadata

| Field | Value |
|---|---|
| **Trace URL** | [fd990dbe-1cc5-4bf8-ba89-a1a9d68d7045](https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/fd990dbe-1cc5-4bf8-ba89-a1a9d68d7045/r) |
| **Model** | `gpt-5.3-chat` |
| **Provider** | OpenAI |
| **Temperature** | 0.0 |
| **Status** | `success` |
| **Duration** | ~9.5 s (12:15:15 → 12:15:24 UTC) |
| **Effective intent** | `assessments-configuration-summary` |

## Run Tree

```
Configuration Agent (chain) ✅ 9.5s
├── flow_router (chain) ✅
│   └── route_flow (chain) ✅
└── assistant (chain) ✅
    ├── ChatOpenAI (llm) ✅  p=3537 c=97
    └── tools_condition (chain) ✅  → END (no tool calls)
```

## Input

```
Show deviations for a specific product family
```

## Output

> To show deviations, I need to scope the findings to a **specific product family**, but none was provided.
>
> Please provide the **product family name** (for example: `ASA`, `Catalyst 9000`, `NX-OS`, etc.).
>
> Once I have that, I can return:
> - Deviation findings (violated rules)
> - Severity distribution
> - Most impacted assets
> - Most violated rules for that product family.

## Message Flow

| Step | Actor | Action |
|---|---|---|
| 1 | **Human** | "Show deviations for a specific product family" |
| 2 | **AI** | No tool calls (`finish_reason: stop`). Responded with clarification request. |

No tool calls were made. The LLM terminated with `stop` instead of `tool_calls`.

## Error Summary

No tool errors — **no tools were called at all**. The graph reports `status: success` despite providing an unhelpful response that fails to use the available tools for data discovery.

## Token Summary

| Step | Node | Prompt | Completion | Total | Cached |
|---|---|---|---|---|---|
| 2 | `ChatOpenAI` | 3,537 | 97 | 3,634 | — |
| **Cumulative** | | **3,537** | **97** | **3,634** | |

## Tool Definitions (bound but unused)

| Tool | Purpose | Product Family Support |
|---|---|---|
| `search_assets_scope` | Normalize asset filters to canonical scope dict | `product_family` as optional filter (all params optional) |
| `query_findings` | Query findings (overview, records, aggregate, distribution) | `group_by=product_family` supported |
| `query_rules` | Query rules (records, aggregate, distribution) | Via `asset_scope` only |
| `query_insights` | Retrieve Signature asset insights | N/A (Signature-only) |

---

## Pattern Analysis

### Agent Behavior

- **The agent did NOT follow its system prompt instructions.** The prompt states "All answers must be grounded in tool results" — yet the agent responded without calling any tools. It interpreted "grounded in tool results" as "don't answer without data" and converted that into "don't even try without all parameters."
- **`finish_reason` is inappropriate.** The agent terminated with `stop` when it should have issued `tool_calls` to discover available product families via `query_findings(group_by="product_family")`.
- **The agent does NOT adapt its strategy.** It chose the worst resolution: halt and ask for clarification with no data-backed options. The user is left guessing valid product family names.

### What the LLM Should Have Done

Called `query_findings` with a distribution view to **discover** available product families:

```json
{
  "name": "query_findings",
  "args": {
    "view_mode": "distribution",
    "group_by": "product_family",
    "status_in": ["deviation"]
  }
}
```

Then presented a response like:

> Here are your deviations by product family:
>
> | Product Family | Deviations | Critical | High |
> |---|---|---|---|
> | Catalyst 9000 | 142 | 12 | 45 |
> | ASA | 87 | 5 | 23 |
> | NX-OS | 64 | 8 | 18 |
>
> Would you like me to drill into a specific product family?

### Token Efficiency

- Prompt tokens: 3,537 (system prompt + tool schemas + user message)
- Completion tokens: 97 (clarification text only — **zero value from tool usage**)
- The entire 3,537-token prompt context (including 4 tool schemas) was wasted since no tools were called

### Latency

- Total: ~9.5 s for a single LLM call with no tool execution
- No bottleneck beyond model inference time

---

## Root Cause

### 1. No ambiguity handling instructions in any system prompt

None of the 4 prompt templates have any guidance on what to do when a query is ambiguous or missing required context:

- `assessments-configuration-summary.md` — no mention
- `asset-scope-analysis.md` — actually says "Require asset-identifying information from the user before calling tools" (encourages halting)
- `rule-analysis.md` — no mention
- `signature-asset-insights.md` — no mention

### 2. Tool-first principle violated

The prompt says "All answers must be grounded in tool results" but doesn't say "always call tools first, even when the query is incomplete." The LLM interpreted this as a reason to stop — not a reason to discover.

### 3. Discovery capability exists but LLM doesn't know to use it

`query_findings` supports `group_by=product_family` which would return a breakdown by product family. But nothing in the prompt tells the LLM to use tools for discovery when the user's query is vague.

### 4. The asset-scope prompt actively encourages this anti-pattern

The `asset-scope-analysis.md` prompt says:

> "**Strategy:** Require asset-identifying or asset-filtering information (hostname, IP, asset key, product family, location, software type/version, or other asset dimension) from the user before calling tools."

This is a prescriptive instruction to halt and ask — the opposite of what we want.

---

## Approach Options

### Option A: Prompt-level ambiguity handling (recommended minimum)

Add an `# Ambiguity Resolution` section to the system prompts instructing the LLM to **use tools to discover data** when the query is unclear, rather than halting. No code changes needed.

**Pros:**
- Simplest approach, zero code risk
- Fast to implement and test
- Works across all skills with a consistent pattern

**Cons:**
- Relies on LLM following instructions (model-dependent)
- May need prompt tuning per model (GPT vs Claude vs Mistral)

### Option B: Intent classifier node

Re-introduce an intent classifier node between `flow_router` and `assistant` that:
- Detects ambiguous/incomplete queries
- Enriches the state with missing context clues
- Could pre-call discovery tools to inject available options into the prompt

**Pros:**
- Deterministic handling, model-agnostic
- Better observability (separate trace step)
- Can enforce business rules about required parameters

**Cons:**
- ~150-250 lines of new code
- Extra LLM call per query (latency + token cost)
- Adds graph complexity

### Option C: Entity extraction pre-processor

A dedicated extraction node that parses entities (product families, hostnames, severities) from the user query and flags what's present vs. missing, then injects a structured context block into the assistant's prompt.

**Pros:**
- Most precise, reusable across all skills
- Enables validation against known values
- Could support auto-complete / suggestion UX in future

**Cons:**
- Needs a reference data source for valid entities (or a discovery tool call)
- Requires per-entity enum maintenance
- Highest implementation cost

## Recommendation

**Start with Option A** (prompt changes). It addresses the immediate problem with zero code risk. The key principle to inject into the prompts:

> **When the user's query is ambiguous or missing a filter value:**
> 1. **Prefer discovery** — If a tool can return available options (e.g. `query_findings` with `group_by=product_family`), call it first and present the results.
> 2. **Fall back to clarifying questions** — If no tool can discover the missing value, or a discovery call returns no data, ask the user a focused clarifying question with concrete examples of what to provide.
> 3. **Never halt silently** — Always respond with either data-backed options or a specific clarifying question. Do not refuse to act without explaining what is needed and why.

If after testing we find the LLM still doesn't reliably follow the ambiguity resolution instructions across models, we can layer on Option B as a deterministic guardrail.
