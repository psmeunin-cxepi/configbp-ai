# Model Capability Baselines

Reference data for Audit Check 5 (Model Capability Alignment).
Last updated: 2026-03-19.

Load the section for the target model being audited.

---

## OpenAI GPT-5

Baseline source: [Prompt guidance for GPT-5.4](https://developers.openai.com/api/docs/guides/prompt-guidance/), [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide/)

- **`reasoning_effort` parameter** — treat as a last-mile tuning knob, not the primary quality lever. Recommended defaults: `none` for execution-heavy workloads (field extraction, triage), `medium`+ for research-heavy (synthesis, multi-doc review). For GPT-5.4, `none` already handles action-selection and tool-discipline tasks well.
- **Prompt-first before raising reasoning** — before increasing `reasoning_effort`, the prompt should include: `<completeness_contract>`, `<verification_loop>`, `<tool_persistence_rules>`, and an initiative nudge.
- **Structured XML specs** — using `<[instruction]_spec>` tags improves instruction adherence and allows clear cross-referencing between prompt sections (validated by Cursor's production testing).
- **GPT-5 is naturally introspective** — avoid over-prompting for thoroughness or context-gathering; this causes unnecessary tool overuse. Soften language around "maximize" and "thorough" to let the model self-regulate.
- **Tool-calling schema** — use OpenAI's native tool-calling format; avoid inline tool instructions in the prompt body.
- **Native structured outputs / JSON mode** — use instead of manual schema enforcement in the prompt.

---

## Anthropic Claude

Baseline source: [Anthropic Prompt Engineering](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering)

- **Adaptive thinking (Opus 4.6, Sonnet 4.6)** — uses `thinking: {type: "adaptive"}` where Claude dynamically decides when and how much to think. Controlled via `effort` parameter (`low`, `medium`, `high`, `max`). Outperforms manual extended thinking in internal evals.
- **Extended thinking (Sonnet 4.6 fallback)** — still supported via `budget_tokens` but adaptive thinking is preferred. Manual CoT with `<thinking>` and `<answer>` tags only when thinking is disabled.
- **XML tag structure** — Claude natively parses XML well. Use descriptive tags (`<instructions>`, `<context>`, `<input>`) to separate content types. Nest tags for hierarchical content. Essential for reducing misinterpretation.
- **Prefer general over prescriptive reasoning instructions** — "think thoroughly" yields better results than rigid step-by-step plans, as Claude's internal reasoning exceeds human-prescribed steps.
- **Few-shot examples** — 3-5 examples wrapped in `<example>` tags. Include `<thinking>` tags in examples to demonstrate reasoning patterns.
- **Long context: data first, query last** — for inputs >20k tokens, place documents at top, instructions at bottom. Can improve quality by up to 30%.
- **Sensitivity to "think" (Opus 4.5 with thinking disabled)** — use alternatives like "consider", "evaluate", or "reason through".

---

## Mistral

Baseline source: [Guardrailing — Mistral AI Docs](https://docs.mistral.ai/capabilities/guardrailing), [Function Calling — Mistral AI Docs](https://docs.mistral.ai/models/pixtral-12b-24-09)

- **Function calling format** — uses OpenAI-compatible `tools` array with `function` objects (`name`, `description`, `parameters` schema). Supports `tool_choice: "auto"` or specific tool selection.
- **`safe_prompt` flag** — set `safe_prompt: true` to prepend a guardrailing system prompt automatically. This is the native guardrailing mechanism — avoid manual safety preambles that duplicate this.
- **Structured outputs** — uses system prompt prepending with schema: "Your output should be an instance of a JSON object following this schema: {{ json_schema }}". Native `response_format` parameter available.
- **System prompt handling** — standard `system` role in messages array. No special turn structure beyond system/user/assistant.
