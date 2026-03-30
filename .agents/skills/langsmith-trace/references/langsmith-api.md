# LangSmith API Reference

Quick reference for the LangSmith REST API endpoints used by this skill.

## Public Shared Traces

Public traces are accessed via share tokens. No authentication is required for public traces, but providing an API key may be needed for some instances.

### Get shared run (root)

```
GET {base_url}/api/v1/public/{share_token}/run
```

Returns the root run of a shared trace, including full inputs, outputs, metadata, and child run IDs.

### Get child run

```
GET {base_url}/api/v1/public/{share_token}/run/{run_id}
```

Returns a specific child run within a shared trace.

## URL Patterns

LangSmith trace URLs follow these patterns:

| Pattern | Example |
|---------|---------|
| SaaS (LangChain hosted) | `https://smith.langchain.com/public/<share_token>/r` |
| Self-hosted / Cisco | `https://langsmith.<env>.<region>.plat.cxp.csco.cloud/public/<share_token>/r` |

The share token is a UUID (e.g., `ef1da42a-c1ae-412e-a4d0-9e2165c3e0b8`).

## Key Fields in Run Response

### Top-level

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Run name (e.g., "ChatOpenAI", "AgentExecutor") |
| `run_type` | string | `llm`, `chain`, `tool`, `retriever`, `prompt`, `parser` |
| `status` | string | `success`, `error`, `pending` |
| `start_time` | ISO datetime | When the run started |
| `end_time` | ISO datetime | When the run completed |
| `error` | string/null | Error message if status is "error" |
| `total_tokens` | int/null | Total token count |
| `prompt_tokens` | int/null | Input token count |
| `completion_tokens` | int/null | Output token count |
| `total_cost` | float/null | Estimated cost in USD |
| `first_token_time` | ISO datetime/null | Time of first streamed token |

### Inputs

`inputs.messages` is typically an array of message arrays. Each message has:
- `id`: Array identifying type (`SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`)
- `kwargs.content`: Message content
- `kwargs.tool_calls`: Array of tool calls (AI messages)
- `kwargs.response_metadata.token_usage`: Per-step token counts
- `kwargs.status`: Tool execution status (`success`, `error`)

### Outputs

`outputs.generations` contains the LLM's output for this step:
- `generations[0][0].message.kwargs.content`: Text response
- `generations[0][0].message.kwargs.tool_calls`: Tool calls made
- `outputs.llm_output.token_usage`: Token usage for this LLM call
- `outputs.llm_output.model_name`: Exact model version used

### Extra / Metadata

`extra.invocation_params` contains:
- `model`: Model name
- `temperature`: Temperature setting
- `tools`: Array of available tool definitions (OpenAI function calling format)

`extra.metadata` contains:
- `ls_model_name`: Normalized model name
- `ls_provider`: Provider (openai, anthropic, etc.)

### Relationships

| Field | Description |
|-------|-------------|
| `trace_id` | ID of the overall trace |
| `parent_run_id` | Parent run (null for root) |
| `child_run_ids` | All descendant run IDs |
| `direct_child_run_ids` | Immediate child run IDs |

## Authentication

```
x-api-key: <LANGSMITH_API_KEY>
```

API keys follow the pattern `lsv2_pt_<hex>_<hex>`.
