# LLM Context Analysis: ConfigBP-AI Agent

**Date**: February 18, 2026  
**Status**: Analysis Complete  
**Priority**: High - Impacts LLM effectiveness

## Executive Summary

This document summarizes a review of the current code and agent implementation, identifying critical gaps in the LLM agent's context and understanding.

**Four Key Issues Identified:**
1. System Prompt - Insufficient domain context
2. MCP Tools - Missing parameter annotations
3. Agent State - Lacks contextual persistence
4. Response Semantics - No guidance on interpreting tool results

---

## 1. System Prompt - Insufficient Domain Context

**Location**: [`agent/config.ini`](agent/config.ini#L17)

### Issues
- **Missing Domain Definitions**: Core terms like "Assessment", "Asset", "Compliance", and "Rules" are never defined
- **Unclear Workflow**: Multi-step MCP workflow (prompts → tools) not explained
- **No Parameter Extraction Guidance**: LLM doesn't know how to extract `assessment_id`, filters, etc. from user queries
- **No Fallback Strategy**: Missing guidance on default behaviors when parameters are absent

### Guiding Principles

1. **Provide Domain Glossary**: Define all domain-specific terms upfront with clear business context
2. **Explicit Workflow Steps**: Document the sequence of operations and explain why each step is necessary
3. **Parameter Extraction Patterns**: Teach LLM how to identify and extract parameters from natural language
4. **Interpretation Guidelines**: Include rules for translating technical data into user-friendly insights

---

## 2. MCP Tools - Missing Parameter Annotations

**Location**: [`mcp_server/server.py`](mcp_server/server.py)

### Issues
- **No Per-Parameter Descriptions**: LLM only sees generic docstring, not field-level guidance
- **Missing Semantic Context**: Parameters like `query_type`, `severity_filter` lack meaning and valid value lists
- **No Extraction Hints**: LLM doesn't know how to map user queries to parameter values
- **Buried Documentation**: Valid options hidden in unstructured docstrings

### Guiding Principles

1. **Use Annotated Field Descriptions**: Leverage `Annotated[type, Field(description="...")]` for structured parameter docs
2. **List Valid Options Explicitly**: Enumerate all valid values with business context (e.g., "critical: immediate action, <24h")
3. **Include Extraction Hints**: Provide patterns for extracting parameters from natural language
4. **Define Default Behaviors**: Clearly state what happens when parameters are omitted
5. **Document Response Schema**: Include expected return structure with field meanings in docstrings

---

## 3. Agent State - Lacks Task-Related Contextual Persistence

**Location**: [`agent/core/state.py`](agent/core/state.py)

**Current State**: Only stores `messages`, `detected_intent`, and `prompt_template`

### Issues
- **No Task State Persistence**: Missing critical task context like `active_assessment_id`, `assessment_results`, `assessment_data`
- **No Tool Call History**: Can't track what tools were invoked and with what parameters
- **No Conversation History Context**: Unable to reference previous queries, answers, or actions
- **No Result Caching**: Can't handle follow-ups like "show me more details" or "filter to critical only"
- **Forces Repetition**: Users must example re-specify or extract `assessment_id` and other context in every message

**Impact**: Task refinement and follow-up questions are broken. The agent has no memory of what it's working on.

### Guiding Principles

1. **Store Active Task Context**: Maintain state keys like `active_assessment_id`, `active_filters`, `current_focus` across conversation
2. **Cache Tool Results**: Keep `assessment_results`, `assessment_data` for follow-up queries without re-fetching
3. **Track Tool History**: Record `tool_call_history` with timestamps, parameters, and results for reference
4. **Preserve Conversation Context**: Maintain `conversation_history` with user intents and agent actions
5. **Enable State-Based Decisions**: LLM should check state first before asking user to repeat information
6. **State Update Pattern**: Nodes return only changed fields; LangGraph persists others automatically

Note : the state keys referenced server as examples, the actual implementation needs to be discussed.

---

## 4. Response Data Semantics - Completely Missing

**Location**: Tool responses - no semantic layer exists

**Current State**: Tools return raw data structures with no semantic annotations, field definitions, or interpretation guidance.

### Issues
- **No Response Schema Documentation**: Tools don't describe return structure or field meanings anywhere
- **No Business Context**: Field names returned from database queries lack interpretation and business meaning
- **No Analysis Patterns**: LLM has zero guidance on identifying systemic vs. isolated issues
- **No Threshold Guidance**: Missing numeric thresholds for decision-making (e.g., "critical >5 = escalate")
- **Raw Data Dumps**: LLM returns unprocessed data because it doesn't understand what the fields mean

**Impact**: This requires SME involvement to provide data annotations that explain what each field means, valid value ranges, business significance, and interpretation rules.

### Guiding Principles

1. **Document Response Schemas**: Add complete schema documentation to tool docstrings with field-by-field explanations
2. **Annotate Business Meaning**: Define business context for each field (e.g., "critical = fix within 24-48h")
3. **Define Interpretation Patterns**: Teach LLM to recognize patterns (frequency >10 = systemic issue)
4. **Specify Decision Thresholds**: Document numeric thresholds that trigger different interpretations
5. **Provide Example Analysis**: Show how to transform raw data into actionable insights
6. **Create Data Dictionary**: Build a comprehensive mapping from technical field names to business language

**Action Required**: SMEs must provide data annotations describing field meanings, value semantics, and interpretation guidelines.

---

## 5. Expected Impact

**Before:**
- LLM struggles with tool parameters and delivers generic responses
- Users must repeat context in every message
- Difficulty interpreting tool results leads to data dumps

**After:**
- Clear understanding of parameters, domain, and workflow
- Natural multi-turn conversations with context persistence
- Actionable insights instead of raw data
- Improved accuracy and user satisfaction

---