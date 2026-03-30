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

Source the `.env` file if present, then run the fetch script with `--mode overview` first:

```bash
source .env 2>/dev/null; python3 .agents/skills/langsmith-trace/scripts/fetch_trace.py "<TRACE_URL>" --mode overview
```

If the script is not at that workspace-relative path, search for `fetch_trace.py` in the workspace or under `~/.agents/skills/langsmith-trace/scripts/`.

### Step 2 — Present the overview

From the overview JSON, present to the user:

1. **Metadata** — Model, provider, temperature, trace ID, status, duration
2. **Run tree** — Hierarchical view of all runs (LLM calls, tool calls, chains)
3. **Input** — What the user asked
4. **Output** — What the agent responded (or which tool it called)
5. **Error summary** — Any tool errors or failures, with the error message
6. **Token summary** — Per-step and cumulative token counts, cache hit rates

Format the overview in Markdown with clear headers and tables.

### Step 3 — Answer follow-up questions

For deeper analysis, fetch additional data using the appropriate mode:

| User asks about | Mode to use |
|---|---|
| Full conversation message history | `--mode messages` |
| Token usage per step, cache rates | `--mode tokens` |
| Available tool definitions/schemas | `--mode tools` |
| Complete raw trace data | `--mode full` |
| Raw API response for debugging | `--mode raw` |

```bash
python3 .agents/skills/langsmith-trace/scripts/fetch_trace.py "<TRACE_URL>" --mode <mode>
```

### Step 4 — Analyze patterns

When analyzing the trace, look for and report on these patterns:

**Error patterns:**
- Repeated identical tool calls (blind retries)
- Tool errors that are transient (5xx) vs. client errors (4xx, validation)
- Misleading error messages (e.g. "fix your mistakes" for server errors)
- Missing error handling or circuit breakers

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
