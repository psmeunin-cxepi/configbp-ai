---
name: langsmith-trace
description: 'Analyze LangSmith traces from any LangSmith instance. Use when: the user shares a LangSmith trace URL, asks to debug an agent run, review token usage, inspect tool calls, diagnose MCP errors, analyze agentic workflows, or troubleshoot LLM agent behavior from trace data.'
argument-hint: 'Paste a LangSmith trace URL (e.g. https://langsmith.../public/<id>/r)'
user-invocable: true
metadata:
  author: psmeunin
  version: "1.0"
---

# LangSmith Trace Analyzer

Analyze LangSmith traces to provide overviews, diagnose issues, and answer questions about agent runs.

## When to Use

- User shares a LangSmith trace URL (`/public/<share_token>/r`)
- User asks to debug, review, or understand an agent run
- User wants token usage breakdown, cost analysis, or latency profiling
- User wants to inspect tool calls, error patterns, or retry behavior
- User asks about MCP tool errors, tool call arguments, or agent decision flow

## Prerequisites

The LangSmith API key must be available. Check these sources in order:
1. `LANGSMITH_API_KEY` environment variable
2. `.env` file in the current workspace (source it first)

If neither is available, ask the user to provide the API key.

## Procedure

### Step 1 — Source environment and fetch the trace

Source the `.env` file if present, then run the fetch script with `--mode raw`:

```bash
source .env 2>/dev/null; python3 .agents/skills/langsmith-trace/scripts/fetch_trace.py "<TRACE_URL>" --mode raw
```

If the script is not at that workspace-relative path, search for `fetch_trace.py` in the workspace or under `~/.agents/skills/langsmith-trace/scripts/`.

**Output format:**
- For `chain` roots (graph-level traces): the script returns `{"root": {...}, "children": [{...}, ...]}` — it automatically fetches all `direct_child_run_ids`.
- For non-`chain` runs (`llm`, `tool`, etc.): the script returns the plain run object.

### Step 2 — Validate run type (GATE)

Check `run_type` in the returned JSON (`root.run_type` for chain traces, or top-level `run_type` for others).

- **If `run_type` is `chain`** — proceed to Step 2. The output already contains root + children.
- **If `run_type` is anything else** (`llm`, `tool`, `retriever`, etc.) — **STOP.** Inform the user:

  > This trace is a `{run_type}`-level run, not a full graph execution (`chain`). It only captures a single step within a larger agent run — it's missing the complete message flow, sibling runs, and graph-level context needed for full analysis.
  >
  > To get the complete picture, please share the **root trace URL** (the top-level `chain` run that contains this step as a child).

  Do **not** proceed with analysis. The data from a non-`chain` run is incomplete and will produce misleading results (e.g. missing system prompt on `chain` roots, missing tool definitions, partial token counts, no graph-level error status).

### Step 3 — Understand the data structure

The script output for a `chain` root contains everything needed for analysis. Here's where each piece of data lives:

**In `root`:**
- Full message sequence: `root.outputs.messages` (human → AI → tool responses → AI, as flat dicts with `type`/`content` keys)
- Graph-level status, duration, aggregated token totals
- Input/output previews

**In `children` (each child is a direct child run):**

| Data needed | Where it lives | How to identify |
|---|---|---|
| System prompt | `llm` child → `inputs.messages[0]` (nested LC format with `kwargs.content`) | Child with `run_type: llm`, look for `SystemMessage` in the `id` field |
| Tool definitions | `llm` child → `extra.invocation_params.tools` | Same `llm` child |
| Model config (temp, max_tokens) | `llm` child → `extra.invocation_params` + `extra.metadata` (`ls_model_name`, `ls_temperature`, etc.) | Same `llm` child |
| Per-LLM-call token breakdown | Each `llm` child → `total_tokens`, `prompt_tokens`, `completion_tokens` | All `llm` children |
| LangGraph step/node metadata | Each child → `extra.metadata` (`langgraph_step`, `langgraph_node`) | Any child |

**Important:** The root uses **flat message format** (dicts with `type`, `content` keys). Child `llm` runs use **LangChain serialization format** (nested dicts with `kwargs`, and class names like `SystemMessage`/`AIMessage` in the `id` array). Handle both formats.

### Step 4 — Extract and correlate

From the root + child data, extract and correlate:

1. **System prompt** — From the first `llm` child's input messages (the `SystemMessage` entry)
2. **Full message sequence** — From root `outputs.messages`: human → AI (with tool_calls) → tool results (with status) → AI response. This is the authoritative conversation flow.
3. **Tool call arguments and responses** — Each AI message's `tool_calls` array paired with subsequent tool messages. Note `status` field (`error` vs `ok`) and full `content`.
4. **Token usage per step** — From each `llm` child: `prompt_tokens`, `completion_tokens`, `cached_tokens` (in `prompt_tokens_details`), `reasoning_tokens` (in `completion_tokens_details`)
5. **Error patterns and retry behavior** — Count tool errors, check if the AI retried (multiple AI→tool→AI cycles), compare tool call arguments across retries
6. **Model and config metadata** — Model name, temperature, max_tokens, provider from the `llm` child's `invocation_params` and `metadata`

### Step 5 — Present the overview

From the extracted data, present to the user:

1. **Metadata** — Model, provider, temperature, trace ID, status, duration, revision
2. **Run tree** — Hierarchical view: root → direct children (with name, run_type, status, duration)
3. **Input** — The user's original message
4. **Output** — The agent's final response to the user
5. **Message flow** — Step-by-step: AI tool calls → tool results → AI response (include tool call arguments and error content)
6. **Error summary** — Any tool errors with full error text, error classification (server vs client)
7. **Token summary** — Per-LLM-call and cumulative token counts, cache hit rates

Format in Markdown with clear headers and tables.

### Step 6 — Respond based on user intent

**If the user provided only a trace URL (no specific question):**

Run the full pattern analysis below and present findings proactively. This is the default behavior when the user just shares a link.

**If the user asked a specific question** (e.g. "which tool was called?", "what was the token usage?", "why did it fail?"):

Answer that question directly using the extracted data from Steps 2–4. Keep the response focused. At the end, suggest:

> I can also run a full pattern analysis on this trace (error patterns, token efficiency, agent behavior, latency). Want me to proceed?

Do **not** run the full analysis unless asked or unless the URL was provided without a question.

#### Full pattern analysis

When performing the full analysis, look for and report on these patterns:

**Error patterns:**
- Repeated identical tool calls (blind retries)
- Tool errors that are transient (5xx) vs. client errors (4xx, validation)
- Misleading error messages (e.g. "fix your mistakes" for server errors)
- Missing error handling or circuit breakers
- Whether the graph reports `status: success` despite user-facing errors

**Token efficiency:**
- Prompt cache hit rate (cached_tokens / prompt_tokens)
- Reasoning token proportion
- Token growth across retry steps
- Whether the context window is being used efficiently

**Agent behavior:**
- Does the agent adapt its strategy after failures?
- Are tool call arguments well-formed?
- Does the agent follow its system prompt instructions?
- Is the finish_reason appropriate (tool_calls vs stop)?
- Does the error response expose internal details (service names, error codes, tool names)?

**Latency:**
- Total duration and per-step duration
- Time to first token (TTFT) if available
- Bottleneck identification (which step is slowest)

## Output Format

Structure all analysis responses in Markdown with:
- Clear headers for each section
- Tables for structured data (token usage, step sequences)
- Code blocks for tool call arguments and raw data
- Bullet lists for findings and recommendations

When the user asks a specific question, focus the answer on that question while providing relevant context from the trace.

## Constraints

- ALL data must come from the trace — never invent or assume trace content
- If a fetch fails, report the error clearly and suggest checking the API key or URL
- Truncate very long content (system prompts, tool responses) to keep output readable
- When quoting tool call arguments, always use JSON code blocks
