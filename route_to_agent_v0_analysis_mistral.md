# Prompt Audit: `route_to_agent` System Prompt

**Target model:** Mistral `mistral-medium-2508`
**Prompt source:** LangSmith trace (Turn 2) — `ChatMistralAI` system message inside `route_to_agent → RunnableSequence`
**Prompt length:** 1,071 chars (system message only); effective context includes 28,805-char Human message with agent cards + conversation history

---

## Original Prompt Under Audit

```
You are a semantic router. Your task is to analyze the user's question and determine
if it is on-topic for any of the available agents. Consider the agent descriptions,
their skills, and the recent conversation context.

If the question is on-topic for an agent, select that agent and one of its skills.
For empty questions and empty context still go through the available agents and skills
and see if one is fit for empty questions. If the user gives greeting like Hi, Thank
you, set the agent_skill to default. If the user asks: 'what can you help you with?',
set the agent_skill to default.

If none of the agents are a good match, you must respond with `is_valid` set to `false`.

CRITICAL: The `agent_skill` field MUST be a simple string containing ONLY the skill
name (e.g., 'select_sav_id_skill'). Do NOT return a nested object, dictionary, or
any structured data for this field. Only return a plain string value.

Respond with a JSON object that strictly follows the `AgentSelectionResponse` schema:
{"is_valid": true/false, "agent_skill": "skill_name_as_string"}
```

**Human message structure (28,805 chars):**
```
AVAILABLE_AGENTS: [{...9 agent cards, ~20K chars JSON...}]

RECENT_CONVERSATION_CONTEXT:
[None] Hello! I can assist you with...
[user] Can you provide a summary of my recent Configuration Assessment?
[Assessments – Configuration] Understanding your request...
[Assessments – Configuration] Thinking about your question...
[Assessments – Configuration] Gathering information...
[Assessments – Configuration] Preparing your answer...
[Assessments – Configuration] # Configuration Assessment Summary ...

USER_QUESTION: can you give me recommendation for C9410R?
```

**Tool definition (1 tool):**
```json
{
  "function": {
    "name": "AgentSelectionResponse",
    "parameters": {
      "properties": {
        "is_valid": { "type": "boolean" },
        "agent_skill": { "type": ["string", "null"], "default": null }
      },
      "required": ["is_valid"]
    }
  }
}
```

---

## Sync Status

- MCP data fetched: **yes** (Context7 — `mistralai/platform-docs-public`, 2026-04-01)
- Delta from training cutoff:
  - Mistral classification prompt example uses `<<<>>>` and `####` delimiters — not reflected in the audited prompt
  - Mistral `safe_prompt: true` flag prepends guardrail text automatically — the audited prompt has no guardrailing (acceptable for internal routing, but noted)
  - Mistral native `response_format` with JSON schema auto-prepends schema instructions — the audited prompt manually enforces schema and uses a tool-call workaround instead
  - Function calling fine-tuning examples confirm standard OpenAI-compatible `tools` format — the tool definition in the audited prompt is structurally valid

---

## Audit Results

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Structural Integrity | **FAIL** | Zero delimiters in system prompt — entire prompt is unstructured prose. Human message uses bare-text labels (`AVAILABLE_AGENTS:`, `RECENT_CONVERSATION_CONTEXT:`, `USER_QUESTION:`) with no XML tags, markdown headers, or Mistral-recommended delimiters (`<<<>>>`, `####`). Agent card JSON (~20K chars) and conversation history (~8K chars) have no structural separation, creating instruction-drift risk. |
| 2 | Instruction Density | **FAIL** | 3 lines spent on empty/greeting edge cases (`"If the user gives greeting like Hi, Thank you, set the agent_skill to default"`), but zero instructions for: multi-turn follow-up detection, disambiguation between keyword matches and contextual signals, conflict resolution when multiple agents match, or how to weight conversation history vs. agent descriptions. The most critical failure mode (follow-up misrouting) is entirely unaddressed. |
| 3 | Ambiguity Elimination | **FAIL** | (a) `"Consider the agent descriptions, their skills, and the recent conversation context"` — "consider" is undefined; no priority order, no weighting, no conflict-resolution rule. (b) `"determine if it is on-topic"` — "on-topic" lacks a testable definition. (c) `"a good match"` — subjective adjective without criteria. (d) Terminology inconsistency: the prompt refers to `agent_skill` but the Human message calls it a "skill name", agent cards use `available_skills`, and the tool schema calls it `agent_skill`. |
| 4 | Modular Layout | **FAIL** | 8 of 10 canonical sections are MISSING or INCOMPLETE. See Section Coverage table below. The prompt is a single block of prose with no structural decomposition. |
| 5 | Model Capability Alignment | **FAIL** | [BASELINE] Manually enforces JSON schema in prompt text (`"Respond with a JSON object that strictly follows..."`) instead of using Mistral's native `response_format` parameter with JSON schema. [BASELINE] Uses tool-calling (`AgentSelectionResponse` function) as a workaround for structured output — this is valid but adds overhead for what is a classification task with a fixed schema. [UPDATED: Context7/mistralai/platform-docs-public] Mistral classification example uses `<<<>>>` and `####` delimiters with few-shot examples — the audited prompt uses neither. [BASELINE] Agent cards (~20K chars of reference data) are placed in the Human message instead of the System message, violating Mistral's message-role conventions where system defines behavior/context and user provides the request. |

---

### Section Coverage

| Section | Status | Notes |
|---------|--------|-------|
| Role | **INCOMPLETE** | `"You are a semantic router"` — no persona depth, no expertise specification, no optimization statement |
| Objective | **INCOMPLETE** | `"analyze the user's question and determine if it is on-topic"` — missing multi-turn objective, no testable success metric |
| Scope | **MISSING** | No explicit in-scope/out-of-scope lists. No boundaries for when the router should reject a query vs. default it |
| Instructions | **INCOMPLETE** | Basic routing logic present but missing: follow-up detection, disambiguation rules, context weighting, conflict resolution, priority ordering between keyword match and context match |
| Toolbox | **INCOMPLETE** | Tool schema defined externally but the system prompt gives no usage guidance — no explanation of when to call the tool or what each field means |
| Output Format | **INCOMPLETE** | JSON schema shown inline (`{"is_valid": true/false, "agent_skill": "..."}`) but not enforced via native Mistral `response_format`. The `CRITICAL` paragraph about string-only fields is a patch for a prior hallucination bug — not a proper output specification |
| Examples | **MISSING** | Zero few-shot examples. This is a critical gap for classification with Mistral — their own docs show few-shot as the primary technique for categorization tasks |
| Validation Checklist | **MISSING** | No self-verification step before emitting the routing decision |
| Special Considerations | **MISSING** | No multi-turn handling, no disambiguation for polysemous terms like "recommendation", no entity-reference resolution rules |
| Runtime Context | **MISSING** | Previous agent name and skill are available in `recent_context_structured` but not injected into the prompt. No `{previous_agent}` or `{previous_skill}` placeholders. Conversation history format not specified |

---

## Critical Flaws

### 1. No Follow-Up / Multi-Turn Routing Logic

**Severity:** Critical
**Impact:** Direct cause of the observed misclassification (Turn 2 → Product Recommendation instead of CBP)

The prompt says "consider the recent conversation context" without defining how. When the user asks "can you give me recommendation for C9410R?" — a direct follow-up referencing an entity (C9410R) that appeared as the #1 result in the previous CBP agent response — the LLM has no rule to prefer the previous agent. It defaults to lexical matching ("recommendation" → Product Recommendation).

**Fix:** Add an explicit Follow-Up Detection section with three heuristics:
1. Entity reference — does the query mention entities from the last agent's response?
2. Anaphoric reference — does the query use "it", "that", "this device"?
3. Topic continuity — does the query naturally extend the previous turn's topic?

If any heuristic fires, route to the same agent. Inject `{previous_agent}` and `{previous_skill}` as runtime context variables.

#### Design Decision: Entity Reference Scope in Long Conversations

Heuristic (1) raises a scoping question for long-running, multi-agent conversations: an entity like `C9410R` may appear in responses from **multiple agents** across many turns. Naively checking "appeared in any previous response" would incorrectly anchor to the wrong agent. Three options were evaluated:

| Option | Strategy | Pro | Con |
|--------|----------|-----|-----|
| **A — Last-turn only** | Check entities against the most recent agent's response only. If no match, treat as new topic. | Simple, predictable | If user wants to return to an earlier agent by referencing its entity, falls through to standard matching — may or may not pick the right agent |
| **B — Entity-to-agent attribution** | Check entities across all prior turns; route to the agent that introduced/primarily discussed that entity. | Handles "go back to Agent A" correctly | Requires structured entity tracking per turn; expensive and error-prone; ambiguous when same entity discussed by multiple agents |
| **C — Sliding window + fallback** | Check entities against the **last 2 agent turns**. If the entity is in the most recent agent's response, route there. If only in the turn before, route to that earlier agent. If no match in the 2-turn window, fall through to standard agent matching (no deep history scan). | Bounded complexity, predictable, handles 90%+ of cases. Covers the common "quick detour then return" pattern | If user references an entity from turn 1 while on turn 8, won't detect as follow-up — but standard matching takes over |

**Selected: Option C.** The 2-turn sliding window keeps the LLM's cognitive load bounded and avoids the "entity appeared 6 turns ago from a different agent" trap. It also handles the common pattern where a user takes a 1-turn detour to a different agent and then returns to the previous topic. For the edge case where a user wants to return to an agent from 3+ turns ago, standard agent matching (with properly enriched agent cards per Flaw #3/R-5) should handle it.

> **Note:** The 2-turn window size is an initial heuristic, not a fixed constant. It should be tuned based on production observations and evaluation — if real conversations regularly exhibit valid follow-ups beyond 2 turns, widen the window. Conversely, if false-positive follow-up matches increase, narrow it. Track routing accuracy by window size as an evaluation metric.

---

### 2. Agent Cards in Human Message (~20K chars)

**Severity:** High
**Impact:** Reference data competes with user query for attention; buries conversation context at position ~20K

The 9 agent cards (~20K chars of JSON) are placed in the Human message. Per Mistral's message-role conventions, reference data that defines the routing context belongs in the System message. The Human message should contain only the user's actual input (conversation history + current question).

**Fix:** Move `AVAILABLE_AGENTS` to the System message. Restructure the Human message to contain only `RECENT_CONVERSATION_CONTEXT` and `USER_QUESTION`, reducing it from ~28K to ~10K chars with the context far more prominent.

---

### 3. Zero Few-Shot Examples

**Severity:** High
**Impact:** Classification without examples relies entirely on instruction-following, which is weaker for edge cases

Mistral's own classification prompt example (Context7) demonstrates the pattern: category list → delimiter → few-shot examples → delimiter → input. The audited prompt provides no examples at all.

**Fix:** Add 2-3 examples covering the critical edge cases:
- Follow-up after assessment → same agent
- New topic with keyword overlap → different agent
- Ambiguous query → fallback behavior

---

### 4. No Structural Delimiters

**Severity:** Medium
**Impact:** Instruction drift risk; model may confuse prompt sections with each other or with user data

The system prompt is unstructured prose. The Human message uses bare-text labels (`AVAILABLE_AGENTS:`, `RECENT_CONVERSATION_CONTEXT:`) without delimiters. Mistral's docs recommend `<<<>>>` for input boundaries and `####` for section breaks.

**Fix:** Use Markdown headers (`##`) in the System prompt for section separation. Use `<<<>>>` delimiters for dynamic user input in the Human message.

---

### 5. Manual Schema Enforcement in Prompt Text

**Severity:** Low
**Impact:** Wasted tokens on schema enforcement that the model's native features handle

The `CRITICAL` paragraph (4 lines, ~280 chars) manually warns the model not to return nested objects for `agent_skill`. This is a patch for a prior hallucination — it should be solved by using Mistral's native `response_format` parameter or by relying on the tool schema's type constraints, not by burning prompt tokens on format-policing.

**Fix:** Use Mistral's native `response_format` with the `AgentSelectionResponse` Pydantic model, or keep the tool-call approach but remove the manual enforcement paragraph — the tool schema already constrains the field to `string | null`.

---

## Refactored Prompt

### System Message

```
## Role
You are a Semantic Router — a classification engine that maps user questions to the
correct agent and skill. You optimize for two equally important goals:
1. Accurate intent classification — routing each question to the best-matching agent.
2. Conversation continuity — detecting follow-up questions and keeping them with the
   agent that has the relevant context.

## Objective
Given a user question and conversation context, select exactly one agent and one skill
from the available agents list below. Return your decision as a tool call to
`AgentSelectionResponse`.

## Follow-Up Detection (EVALUATE FIRST)
Before matching the question to an agent by description, determine whether the question
is a follow-up to a recent agent turn.

Scope: Only consider the LAST 2 AGENT TURNS (the most recent agent response and the
one before it). Do NOT scan the full conversation history for entity matches.

A question is a follow-up if ANY of the following are true:

1. **Entity reference**: The question mentions a device name, hostname, PID, rule name,
   or other entity that appeared in the last 2 agent responses. Route to the agent
   whose response contained that entity. If both agents mentioned it, prefer the
   most recent.
2. **Anaphoric reference**: The question uses "it", "that", "this", "the same",
   "those", or similar pronouns that resolve to entities in the last agent's response.
3. **Topic continuity**: The question asks for details, recommendations, drilldown,
   or next steps on the topic the last agent was handling.

If the question IS a follow-up:
→ Route to the agent whose response contained the matched entity or topic.
→ Select the skill from that agent that best matches the follow-up scope.
→ Do NOT switch agents based on keyword overlap alone.

If the question references an entity NOT found in the last 2 agent responses:
→ Treat as a NEW TOPIC. Match against all available agents using standard routing.
→ Do NOT attempt to trace the entity back beyond the 2-turn window.

## Available Agents
<<<AGENTS
{available_agents_json}
AGENTS>>>

## Routing Instructions
1. If the question is a follow-up (per rules above), route to the previous agent.
2. If the question is a new topic, match it to the agent whose description and skill
   set best fits the user's intent. Prefer semantic match over keyword match.
3. For greetings ("Hi", "Thank you") or meta-questions ("What can you help me with?"),
   set `agent_skill` to `"default"`.
4. For empty questions with empty context, check if any agent handles empty-state
   interactions and route there; otherwise set `is_valid` to `false`.
5. If no agent is a good match, set `is_valid` to `false` and `agent_skill` to `null`.

## Output Format
Call the `AgentSelectionResponse` tool with exactly two fields:
- `is_valid` (boolean): `true` if an agent matches, `false` otherwise
- `agent_skill` (string): The skill name as a plain string, e.g. `"asset-scope-analysis"`.
  Must be a flat string — never a nested object.

## Examples

####
Example 1 — Follow-up after assessment:
Previous agent: Assessments – Configuration (assessments-configuration-summary)
Previous response: Listed C9410R as top impacted asset (630 violations, 74 rules)
Question: "can you give me recommendation for C9410R?"
Reasoning: C9410R appeared in the previous response → follow-up → same agent
→ {"is_valid": true, "agent_skill": "asset-scope-analysis"}

Example 2 — New topic, keyword overlap:
Previous agent: LDOS Analysis (ask_cvi_ldos_ai_external)
Previous response: Listed 45 assets past LDOS dates
Question: "I want recommendation for WS-C2960S-48TS-L"
Reasoning: WS-C2960S-48TS-L is NOT in the previous response. User wants product
replacement info. → new topic → match to Product Recommendation agent
→ {"is_valid": true, "agent_skill": "ask_cvi_recommendation_ai"}

Example 3 — Follow-up with anaphoric reference:
Previous agent: Assessments – Configuration (asset-scope-analysis)
Previous response: Showed 74 rule violations for C9410R
Question: "which of those are the most critical?"
Reasoning: "those" refers to rule violations from the previous response → follow-up
→ {"is_valid": true, "agent_skill": "asset-scope-analysis"}
####

## Validation Checklist
Before emitting your response, verify:
- [ ] Did I check follow-up detection rules BEFORE matching by agent description?
- [ ] If the question references an entity from a recent agent response, am I routing
      to the agent whose response contained that entity?
- [ ] Am I only checking the last 2 agent responses for entity matches (not the full
      conversation history)?
- [ ] Is `agent_skill` a plain string (not a nested object)?
- [ ] Does the selected skill exist in the selected agent's skill list?
```

### Human Message

```
## Previous Turn
Previous agent: {previous_agent_name}
Previous skill: {previous_agent_skill}

## Recent Conversation
{cleaned_conversation_history}

## Current Question
<<<
{user_question}
>>>
```

### Notes on the Refactored Prompt

1. **Agent cards moved to System message** — wrapped in `<<<AGENTS ... AGENTS>>>` delimiters per Mistral conventions. The Human message is reduced from ~28K to ~10K chars.

2. **Follow-Up Detection is the first evaluation step** — placed before general routing instructions so the model evaluates it before matching keywords. Uses a **2-turn sliding window** (Option C) to avoid false follow-up matches from deep history while still handling the common "quick detour then return" pattern. This directly addresses RC-1 (the root cause of the observed misclassification).

3. **Three few-shot examples** cover the critical edge cases: follow-up with entity reference, new topic with keyword overlap ("recommendation"), and anaphoric follow-up. These align with Mistral's classification prompt pattern from their docs.

4. **`{previous_agent_name}` and `{previous_agent_skill}` are runtime variables** — injected from `recent_context_structured`, which already contains this data. This addresses RC-5.

5. **`{cleaned_conversation_history}`** should strip progress/status messages ("Understanding your request...", "Thinking about your question...", etc.) and use the structured `[agent_name]` prefixes. This addresses RC-4.

6. **The `CRITICAL` paragraph about string-only fields** is retained as a single line in the Output Format section. For a production improvement, consider switching to Mistral's native `response_format` parameter to eliminate this entirely (see Recommendation R-7 in the analysis).

7. **The tool definition (`AgentSelectionResponse`)** remains unchanged — it is structurally valid for Mistral's function-calling format.

---

## Citations

- [Mistral Classification Prompt Example](https://github.com/mistralai/platform-docs-public/blob/main/docs/guides/prompting-capabilities.md) — demonstrates `<<<>>>` delimiters, `####` section breaks, category list → few-shot examples → input structure for classification tasks (Context7, 2026-04-01)
- [Mistral Function Calling Fine-Tuning Format](https://github.com/mistralai/platform-docs-public/blob/main/docs/capabilities/finetuning/text-finetuning.mdx) — confirms OpenAI-compatible `tools` array with `function` objects (Context7, 2026-04-01)
- [Mistral Guardrailing — `safe_prompt` Flag](https://docs.mistral.ai/capabilities/guardrailing) — native guardrailing mechanism via boolean flag; avoid duplicating in prompt text [BASELINE]
- [Mistral Structured Outputs](https://docs.mistral.ai/) — native `response_format` parameter auto-prepends JSON schema; alternative to tool-call workaround [BASELINE]
- [System Prompt Guide](references/system-prompt-guide.md) — canonical 10-section template used for Section Coverage audit [BASELINE]
- [Model Baselines — Mistral](references/model-baselines.md) — function calling format, `safe_prompt`, structured outputs, message-role conventions [BASELINE]
