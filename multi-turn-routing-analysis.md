# Multi-Turn Routing Analysis: Semantic Router Misclassification

**Date:** 2026-04-01

| Turn | User Prompt | Expected Agent | Actual Agent | Correct? |
|------|------------|----------------|--------------|----------|
| 1 | "Can you provide a summary of my recent Configuration Assessment?" | Assessments – Configuration | Assessments – Configuration | Yes |
| 2 | "can you give me recommendation for C9410R?" | Assessments – Configuration | Product Recommendation | **No** |

**Traces:**

| Turn | Trace URL |
|------|-----------|
| 1 | [LangSmith](https://langsmith.nprd.usw2.plat.cxp.csco.cloud/public/4f7bf759-14b7-46e9-8cef-0944f2534875/r) |
| 2 | [LangSmith](https://langsmith.nprd.usw2.plat.cxp.csco.cloud/public/69b1b31f-574c-4fc5-aecd-92523d5388ec/r) |

---

## Executive Summary

The Semantic Router correctly routes Turn 1 via static keyword matching but **misclassifies Turn 2** when it falls back to its LLM classifier (Mistral `mistral-medium-2508`). The follow-up question "can you give me recommendation for C9410R?" — clearly referring to the C9410R device listed as the top impacted asset in Turn 1's Configuration Assessment — is routed to the **Product Recommendation** agent instead of back to the **Assessments – Configuration (CBP)** agent.

The root causes are:

1. **The system prompt has no multi-turn/follow-up handling instructions** — it tells the LLM to "consider the recent conversation context" but gives no rules for how to use it
2. **Agent cards are injected into the Human message** instead of the System prompt, causing them to compete with the conversation context for attention
3. **Keyword bias** — "recommendation" in the user prompt lexically matches the Product Recommendation agent's name, description, skill name, tags, and example questions, overwhelming the contextual signal from conversation history
4. **The conversation context is buried** at the bottom of a 28K-char Human message, below 20K+ chars of agent card JSON

---

## Architecture: Semantic Router Pipeline

Both traces reveal the same 7-step graph executed by the "Semantic Router" chain:

```
check_if_customer → fetch_recent_context_db → fetch_agent_candidates_db → generate_title → create_conversation_db → route_to_agent → execute_agent
```

### Routing Mechanism (Two-Tier)

The `route_to_agent` node uses a **two-tier approach**:

| Tier | Method | When Used | Turn 1 | Turn 2 |
|------|--------|-----------|--------|--------|
| **Static routing** | Keyword/rule matching (no LLM) | When the question matches known patterns | **Used** (`is_static_routing: true`) | Failed |
| **LLM routing** | ChatMistralAI classifier | Fallback when static routing has no match | Skipped | **Used** (`is_static_routing: false`, `llm_provider: mistral_backup`) |

**Observation:** Turn 1 succeeded because "Configuration Assessment" is a strong keyword match for the CBP agent. Turn 2 failed because "recommendation for C9410R" doesn't match any CBP static patterns — and the LLM fallback misclassified it.

**Note:** `llm_provider: mistral_backup` suggests the primary LLM provider was also unavailable, and this was a backup Mistral instance.

---

## Turn 1: Correct Routing (Baseline)

| Metric | Value |
|--------|-------|
| Root chain | Semantic Router |
| Duration | 44.1s |
| Total tokens | 14,152 |
| Routing method | Static (`is_static_routing: true`) |
| Selected agent | Assessments – Configuration |
| Selected skill | `assessments-configuration-summary` |

**Flow:**
1. Static rules matched "Configuration Assessment" → CBP agent
2. No LLM call needed for routing (0 tokens in `route_to_agent`)
3. `execute_agent` dispatched to CBP → received full assessment summary (44.1s, 14,152 tokens)

**CBP Response Highlights:**

The CBP agent returned a detailed assessment with C9410R listed as the **#1 most impacted asset**:

| Hostname | Violations | Distinct Rules Violated |
|----------|-----------|------------------------|
| **C9410R** | **630** | **74** |
| ISR4331/K9 | 364 | 74 |
| C9407-R-2 | 220 | 74 |

The response ended with: *"If helpful, I can also: Identify the highest-risk violations to remediate first..."* — which is exactly what the user followed up on in Turn 2.

---

## Turn 2: Misclassified Follow-Up (Detailed Analysis)

| Metric | Value |
|--------|-------|
| Root chain | Semantic Router |
| Duration | 9.2s |
| Total tokens | 7,368 |
| Routing method | LLM (`is_static_routing: false`) |
| LLM provider | `mistral_backup` |
| LLM model | `mistral-medium-2508` |
| Temperature | 0.0 |
| Tokens | prompt: 7,341 / completion: 27 |
| Selected agent | Product Recommendation |
| Selected skill | `ask_cvi_recommendation_ai` |
| **Expected agent** | **Assessments – Configuration** |
| **Expected skill** | **`asset-scope-analysis`** |

**Run tree:**

```
Semantic Router (chain, 9.2s, 7368 tokens)
├── check_if_customer (chain, 0.0s)
├── fetch_recent_context_db (chain, 0.0s)
├── fetch_agent_candidates_db (chain, 0.0s)
├── generate_title (chain, 0.0s)
├── create_conversation_db (chain, 0.0s)
├── route_to_agent (chain, 3.5s, 7368 tokens)
│   ├── RunnableSequence (chain, 1.1s)
│   │   ├── ChatMistralAI (llm, 1.1s, 7368 tokens)
│   │   └── PydanticToolsParser (parser, 0.0s)
│   └── route_after_agent_choice (chain, 0.0s)
└── execute_agent (chain, 5.6s, 0 tokens)
    └── route_after_execution (chain, 0.0s)
```

### What Mistral Received

**System message** (1,071 chars):
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

**Human message** (28,805 chars):
```
AVAILABLE_AGENTS: [{...JSON of 9 agents with full descriptions, skills, URLs...}]

RECENT_CONVERSATION_CONTEXT:
[None] Hello! I can assist you with...
[user] Can you provide a summary of my recent Configuration Assessment?
[Assessments – Configuration] Understanding your request...
[Assessments – Configuration] Thinking about your question...
[Assessments – Configuration] Gathering information...
[Assessments – Configuration] Preparing your answer...
[Assessments – Configuration] # Configuration Assessment Summary
... (full CBP response including C9410R as top impacted asset) ...

USER_QUESTION: can you give me recommendation for C9410R?
```

**Tool definition** (1 tool):
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

**LLM Output:**
```json
{"agent_skill": "ask_cvi_recommendation_ai", "is_valid": true}
```

### What the User Received

The Product Recommendation agent returned a generic capabilities message:

> *"I'm a specialized assistant for Cisco Catalyst, Nexus, and UCS server product information and recommendations. [...] Your question either doesn't appear to be related to Cisco products or given product lines. Please ask me about Cisco Catalyst switches, Nexus switches, or UCS servers instead!"*

The question was passed to the Product Recommendation agent with the appended conversation history, but that agent couldn't answer the configuration assessment question either.

---

## Root Cause Analysis

### RC-1: No Multi-Turn / Follow-Up Instructions (Critical)

The system prompt says *"Consider the agent descriptions, their skills, and the recent conversation context"* but provides **zero guidance** on:

- How to identify a follow-up question
- How to use conversation history for disambiguation
- Whether to prefer the previously-used agent when context is ambiguous
- How to resolve conflicts between keyword matches and contextual signals

**Without explicit rules, the LLM defaults to lexical matching** — "recommendation" → Product Recommendation.

**Evidence:** The conversation context clearly shows:
1. The user previously asked about Configuration Assessment
2. The CBP agent responded with C9410R data
3. The user's follow-up references C9410R by name
4. The CBP agent explicitly offered to provide further analysis ("I can also: Identify the highest-risk violations to remediate first")

A single follow-up heuristic would have resolved this.

### RC-2: Agent Cards in Human Message Instead of System Prompt (High)

The 9 agent cards (~20K chars of JSON) are placed in the **Human message**, not the System prompt. This is architecturally wrong for Mistral:

**Per Mistral docs:**
- *"A system message sets the behavior and context for an AI assistant"*
- *"A user message provides a request, question, or comment that the AI assistant should respond to"*

The agent cards are **reference data that defines the routing context**, not user input. By placing them in the Human message:

1. They compete with the user's actual question and conversation context for attention
2. The model treats them as part of the "user request" rather than as authoritative reference data
3. The 20K chars of agent JSON drowns out the 2K chars of conversation context that follows it

**Recommended:** Move `AVAILABLE_AGENTS` to the System prompt. Keep only `RECENT_CONVERSATION_CONTEXT` and `USER_QUESTION` in the Human message.

### RC-3: Keyword Dominance — "recommendation" (High)

The word "recommendation" in the query creates overwhelming lexical signal:

| Source | Match Text |
|--------|-----------|
| Agent name | "**Product Recommendation**" |
| Agent description | "**Recommends** products based on customer input" |
| Skill name | "ask_cvi\_**recommendation**\_ai" |
| Skill description | "**Recommends** products based on customer input, answers energy related questions" |
| Skill tags | `["recommendation"]` |
| Example questions | "I want **recommendation** for WS-C2960S-48TS-L" |

Meanwhile, the CBP agent card uses none of these keywords. Its closest matches:
- Skill `asset-scope-analysis`: "Findings and rule impact for one or more assets or a filtered asset set"
- Skill description: "Scoped by device, hostname, product family..."

The word "recommendation" in the CBP context means **remediation recommendation** (fix configuration deviations), not **product recommendation** (replace hardware). But the agent cards don't distinguish between these meanings.

### RC-4: Conversation Context Buried and Poorly Formatted (Medium)

The `RECENT_CONVERSATION_CONTEXT` section is placed **after** all agent cards in the Human message. The structure is:

```
AVAILABLE_AGENTS: [...20K chars of JSON...]
RECENT_CONVERSATION_CONTEXT: [...~8K chars of conversation history...]
USER_QUESTION: ...the actual question...
```

Problems:
1. **Position:** Agent cards consume the first 70% of the Human message. The conversation context that explains why "recommendation for C9410R" is a follow-up is buried at position ~20K
2. **Format:** The context mixes status messages ("Understanding your request...", "Thinking about your question...", "Gathering information...", "Preparing your answer...") with actual responses. These progress indicators are noise and dilute the signal
3. **No structural markers:** The context uses informal `[None]`, `[user]`, `[Assessments – Configuration]` prefixes instead of structured delimiters. There's no explicit marker distinguishing "previous agent" from "previous question"
4. **Agent attribution not highlighted:** The fact that "Assessments – Configuration" handled the previous turn is buried in the message prefix labels, not surfaced as a routing signal

### RC-5: Missing Conversational State in Routing Decision (Medium)

The `route_to_agent` node receives `recent_context_structured` (a JSON object with full chat history including `agent_name` and `agent_skill` for each turn), but the LLM only sees a flattened text version in the Human message. The structured data — which explicitly says `"agent_name": "Assessments – Configuration"` and `"agent_skill": "assessments-configuration-summary"` — is **not used** in the LLM prompt.

If the system prompt included a simple rule like:

> *"The user's previous question was handled by agent `{previous_agent_name}` using skill `{previous_agent_skill}`. If the current question references entities from the previous response, prefer routing to the same agent."*

...the misclassification would not have occurred.

---

## Prompt Audit: `route_to_agent` System Prompt (Mistral-Aligned)

A full prompt audit was performed using the prompt-auditor skill against the 1,071-char system prompt. **All 5 checks failed.** 8 of 10 canonical sections are MISSING or INCOMPLETE.

Key findings:

| # | Check | Result | Top Issue |
|---|-------|--------|-----------|
| 1 | Structural Integrity | **FAIL** | Zero delimiters — unstructured prose, no `<<<>>>` or `####` per Mistral conventions |
| 2 | Instruction Density | **FAIL** | 3 lines on greetings, 0 lines on follow-up detection (the actual failure mode) |
| 3 | Ambiguity Elimination | **FAIL** | "Consider", "on-topic", "good match" — undefined subjective terms |
| 4 | Modular Layout | **FAIL** | 8/10 canonical sections MISSING or INCOMPLETE |
| 5 | Model Capability Alignment | **FAIL** | Manual schema enforcement instead of native `response_format`; agent cards in Human message |

The audit identified 5 critical flaws, a complete refactored prompt with a 2-turn sliding window for follow-up detection, 3 few-shot examples, and a restructured Human message.

**Full audit details:** See [route_to_agent_v0_analysis_mistral.md](route_to_agent_v0_analysis_mistral.md) for the complete audit output including section coverage table, critical flaws with fixes, the refactored prompt, and Mistral documentation citations.

---

## CBP Agent: High-Level Multi-Turn Context

The CBP agent (Assessments – Configuration) operates correctly within its own scope. Relevant observations for the multi-turn scenario:

| Aspect | Observation |
|--------|-------------|
| Turn 1 response | Complete, well-structured, includes actionable follow-up offers ("I can also: Identify the highest-risk violations to remediate first") |
| C9410R prominence | Top of the "Most Impacted Assets" table — 630 violations, 74 rules violated |
| Follow-up hook | The response naturally invites "recommendation" follow-ups about asset remediation |
| Agent card gap | The CBP agent card does not include "recommendation" or "remediation recommendation" anywhere in its skill descriptions or tags — making it invisible to keyword-based routing |
| Skill match | `asset-scope-analysis` ("Findings and rule impact for one or more assets, scoped by device, hostname...") would have been the correct skill for "recommendation for C9410R" |
| Available questions gap | None of the CBP `available_questions` include the word "recommendation" — yet it's a natural user intent after reviewing assessment findings |

**Recommendation for CBP agent card:** Add "recommendation" and "remediation" to the `asset-scope-analysis` skill description and tags, and add an example question like: *"What are the configuration recommendations for C9410R?"*

---

## Recommendations

### R-1: Add Multi-Turn Routing Rules to System Prompt (Critical)

Add an explicit Follow-Up Detection section evaluated **before** standard agent matching, with three heuristics:

1. **Entity reference** — does the query mention entities (device names, hostnames, PIDs) from recent agent responses?
2. **Anaphoric reference** — does the query use "it", "that", "this", "the same", "those" to refer to entities in the last agent's response?
3. **Topic continuity** — does the query ask for details, recommendations, drilldown, or next steps on the topic the last agent was handling?

If any heuristic fires → route to the agent whose response contained the matched entity or topic.

**Entity reference scope:** For long-running, multi-agent conversations, entities may appear in responses from multiple agents. A 2-turn sliding window (check the last 2 agent responses, prefer most recent on ties) balances accuracy with bounded complexity. The window size should be tuned based on production evaluation. See [Design Decision: Entity Reference Scope](route_to_agent_v0_analysis_mistral.md#design-decision-entity-reference-scope-in-long-conversations) in the prompt audit for the full Options A/B/C analysis.

Inject `{previous_agent_name}` and `{previous_agent_skill}` as runtime context variables from `recent_context_structured`.

### R-2: Move Agent Cards to System Prompt (High)

Per Mistral docs, reference data should be in the System message. Restructure:

**System message:**
```
[Current system prompt instructions]

## Available Agents
[Agent cards JSON or structured summary]
```

**Human message:**
```
## Recent Conversation
Previous agent: {agent_name}
Previous skill: {agent_skill}

{conversation_history — cleaned, no status messages}

## Current Question
{user_question}
```

This reduces the Human message from ~28K to ~10K chars (conversation history is ~8K), making the conversation context and user question dominant.

### R-3: Add Few-Shot Examples for Follow-Up Routing (High)

Mistral's classification performance improves significantly with few-shot examples — their own docs demonstrate this as the primary technique for categorization tasks. Add 3 examples covering the critical edge cases:

1. **Follow-up with entity reference** — "can you give me recommendation for C9410R?" after CBP listed C9410R → same agent (`asset-scope-analysis`)
2. **New topic with keyword overlap** — "I want recommendation for WS-C2960S-48TS-L" after LDOS analysis → different agent (`ask_cvi_recommendation_ai`)
3. **Follow-up with anaphoric reference** — "which of those are the most critical?" after CBP showed 74 rule violations → same agent (`asset-scope-analysis`)

These examples explicitly teach the model that "recommendation for [device]" can route to different agents depending on conversation context, and that pronouns like "those" should resolve to the last agent's response.

See the [Refactored Prompt](route_to_agent_v0_analysis_mistral.md#examples) in the prompt audit for the complete few-shot examples.

### R-4: Clean Up Conversation Context (Medium)

Remove noise from `RECENT_CONVERSATION_CONTEXT`:
- Strip progress/status messages ("Understanding your request...", "Thinking about your question...", "Gathering information...", "Preparing your answer...")
- Replace `[None]` prefix with a proper label
- Add explicit metadata: `Previous Agent: Assessments – Configuration`, `Previous Skill: assessments-configuration-summary`

### R-5: Enrich CBP Agent Card with "Recommendation" Vocabulary (Medium)

Add to the `asset-scope-analysis` skill:
- Description: append *"...including remediation recommendations and corrective actions for specific assets."*
- Tags: add `"recommendation"`, `"remediation"`
- Available questions: add *"What are the configuration recommendations for C9410R?"*, *"Give me recommendations for [hostname]"*

This ensures the CBP agent is a candidate even for pure keyword matching when "recommendation" appears in an assessment context.

### R-6: Inject Previous-Agent Metadata as Routing Signal (Medium)

The `recent_context_structured` already contains `agent_name` and `agent_skill` for each turn. Inject these into the LLM prompt directly instead of making the model parse them from the conversation history:

```python
# In the prompt template
previous_agent = recent_context_structured["chat_history"][-1].get("agent_name", "None")
previous_skill = recent_context_structured["chat_history"][-1].get("agent_skill", "None")
```

### R-7: Use Mistral Native Structured Output Instead of Tool-Call Workaround (Low)

The current implementation uses a tool call (`AgentSelectionResponse`) to get structured JSON output. Mistral natively supports `response_format` with JSON schema — use this instead:

```python
response = client.chat.parse(
    model="mistral-medium-2508",
    messages=[...],
    response_format=AgentSelectionResponse,  # Pydantic model
)
```

This is cleaner and avoids the tool-calling overhead for what is fundamentally a classification task.

---

## Summary of Findings

| # | Finding | Severity | Category |
|---|---------|----------|----------|
| 1 | No multi-turn/follow-up handling in system prompt | **Critical** | Prompt Design |
| 2 | Agent cards in Human message instead of System prompt | **High** | Prompt Architecture |
| 3 | "recommendation" keyword dominates over conversation context | **High** | Disambiguation |
| 4 | No few-shot examples for classification | **High** | Mistral Alignment |
| 5 | Conversation context buried under 20K of agent JSON | **Medium** | Message Structure |
| 6 | Progress/status messages pollute conversation context | **Medium** | Data Hygiene |
| 7 | Previous agent name/skill not injected as explicit routing signal | **Medium** | Context Engineering |
| 8 | CBP agent card lacks "recommendation" vocabulary | **Medium** | Agent Card Design |
| 9 | Tool-call workaround instead of native structured output | **Low** | Mistral Alignment |

---

## Appendix: Token Usage Comparison

| Metric | Turn 1 | Turn 2 |
|--------|--------|--------|
| Total tokens | 14,152 | 7,368 |
| Routing tokens | 0 (static) | 7,368 (LLM) |
| Agent execution tokens | 14,152 | 0 |
| Agent execution duration | 44.1s | 5.6s |
| Routing duration | 0.0s | 3.5s |
| **Outcome** | **Correct** | **Misclassified** |
| User received | Detailed CBP assessment summary | Generic Product Recommendation capabilities list |

The 7,368 routing tokens in Turn 2 were entirely wasted — they produced a wrong classification that led to 0 useful agent tokens and a meaningless response to the user.
