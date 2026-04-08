---
name: agent-card-auditor
description: Review, validate, and rewrite A2A AgentCard manifests for protocol compliance and routing quality. Use when auditing A2A agent cards, fixing AgentCard or AgentSkill fields, improving descriptions, tags, and examples, or separating schema requirements from style heuristics.
metadata:
  version: "0.0.12"
  method: "protocol-compliance + routing-quality audit"
---

# Agent Card Auditor

Use this skill to audit an A2A AgentCard in a way that is strict about the published schema and explicit about any non-schema recommendations.

## How to Invoke

Provide one of the following:

- a complete AgentCard manifest
- a file path to an AgentCard manifest
- a pasted excerpt plus a request to review or rewrite specific fields

If the user wants the revised card to be saved after the audit, determine the source file path before writing versioned outputs.

## Scope

This skill evaluates an A2A AgentCard in three layers:

1. Protocol Compliance
2. Routing Quality Heuristics
3. Optional House Rules

Never present a heuristic or house rule as if it were a protocol requirement.

## Source of Truth

Ground all protocol checks in the current A2A definitions:

- https://a2a-protocol.org/latest/definitions/

If the workspace contains a local schema, spec snapshot, or team guidance that is clearly newer or more specific than the public reference, use it and note that source in the report.

## Protocol Compliance

Use these facts as the minimum schema baseline for audits:

- `AgentCard` requires `name`, `description`, `supported_interfaces`, `version`, `capabilities`, `default_input_modes`, `default_output_modes`, and `skills`.
- In the published A2A v1 schema, `AgentCard` does not include a top-level `id` field.
- `AgentSkill` requires `id`, `name`, `description`, and `tags`.
- `AgentSkill.examples` is optional in the published schema.
- `Artifact.description` is optional.

For all other protocol questions, refer to the source defined in `## Source of Truth` rather than inferring rules from examples.

If a card uses custom fields or extension-specific conventions, preserve them unless they conflict with the protocol or the user asked for a strict normalization pass.

## Heuristics For High-Quality Routing

Use these heuristics to improve routing quality. They are non-normative interpretations of the protocol field purposes, optimized for agent discovery and routing.

### AgentCard.description

Protocol purpose: help users and other agents understand the agent's purpose.

Prefer one or two sentences that answer:

- What does this agent do well?
- Where should requests stop being routed here?

Good descriptions make the agent's purpose easy to understand and easy to distinguish from nearby agents.

Avoid:

- Long inventories of everything the agent might do
- Vague phrases such as `handles various tasks`
- Internal architecture details
- Empty adjectives such as `smart`, `advanced`, or `powerful`

### AgentSkill.description

Protocol purpose: provide a detailed description of the skill.

Prefer a concrete action-target-outcome pattern.

Examples:

- `Validates CRM account records and flags missing ownership or lifecycle fields.`
- `Creates renewal risk summaries from account history and customer health signals.`

Avoid:

- Restating only the skill name
- Describing internal implementation steps
- Overly broad claims that overlap heavily with other skills

### AgentSkill.tags

Protocol purpose: provide keywords describing the skill's capabilities.

Prefer tags that help a router connect user language to the skill's capabilities.

Good tag categories include:

- domain terms
- task verbs
- artifact or entity types
- user-facing synonyms

Avoid:

- opaque internal codes
- purely promotional words
- tags that duplicate each other with no routing value

### AgentSkill.examples

Protocol purpose: show example prompts or scenarios that the skill can handle.

If examples are present, they should look like realistic prompts or short scenarios that a user or orchestrator might provide.

Good examples are:

- short
- concrete
- aligned with the skill boundary
- distinct from each other

Avoid examples that are:

- too generic to route meaningfully
- implementation-specific
- inconsistent with the skill description

## Audit Workflow

Follow this sequence.

### 1. Parse the manifest

- Identify whether the input is JSON or YAML.
- Parse the full AgentCard.
- If the manifest is malformed, stop the protocol audit, explain the parse failure, and provide a corrected manifest only if the intended structure is still recoverable.

### 2. Run protocol compliance checks

Apply the rules and facts defined in `## Protocol Compliance`.

Check only against fields and constraints that are supported by the published A2A schema or a user-provided authoritative schema.

Examples of valid protocol findings:

- Missing required field
- Wrong published field name
- Wrong container shape
- Empty or unusable required collection
- Interface URL is not an absolute HTTPS URL for production guidance

For every protocol finding:

- Name the exact field
- State whether it is `FAIL` or `WARNING`
- Quote the evidence from the manifest
- Explain the minimum correction needed

### 3. Run routing-quality review

Apply the heuristics defined in `## Heuristics For High-Quality Routing`.

After protocol checks, review whether the card is easy for an LLM router to discriminate from nearby agents.

Treat these as heuristics, not schema rules.

Evaluate at least these fields when present:

- `AgentCard.description`
- `AgentSkill.description`
- `AgentSkill.tags`
- `AgentSkill.examples`

Also check for terminology consistency across the card and for implementation detail that dilutes routing intent.

### 4. Apply optional house rules

Only apply this section if one of these is true:

- The user explicitly asks for stricter internal standards
- The workspace provides local conventions
- The existing card already follows a clear team-specific pattern and the task is to preserve it

Possible house rules may include:

- Minimum number of tags
- Minimum number of examples
- Required style for tags such as lowercase `kebab-case`
- Required phrasing such as `Route here when...`
- Internal taxonomy constraints such as domain tags plus action tags

If you apply a house rule, label it `HOUSE RULE` in the report and identify the source if known.

### 5. Rewrite conservatively

When producing a corrected card:

- Preserve valid fields and values where possible
- Fix only what is required for compliance or clearly improves routing quality
- Do not invent capabilities that are not supported by the source manifest
- Do not remove custom fields unless they are invalid, misleading, or the user asked for strict normalization
- Keep wording specific and operational, not promotional

## Output Contract

Use this report structure.

Always separate protocol findings, routing heuristics, and house rules. Do not merge them into a single undifferentiated findings list.

## A2A Audit Report: [Agent Name]

**Overall Status:** PASS | WARNING | FAIL

### 1. Protocol Compliance

| Field | Result | Evidence | Fix |
|---|---|---|---|
| `skills[0].description` | FAIL | Missing required value | Add a non-empty description |

### 2. Routing Quality Heuristics

| Field | Result | Observation | Suggested Improvement |
|---|---|---|---|
| `skills[1].tags` | WARNING | Uses internal labels only | Replace with user-intent keywords |

### 3. House Rules

State `Not Applied` if no house rules were used.

### 4. Critical Issues

List only the highest-impact problems that block protocol correctness or likely routing quality.

### 5. Revised AgentCard

Provide a full corrected manifest only when the user asked for a rewrite or when the current manifest is materially broken.

If you emit a corrected manifest:

- Preserve the input format when practical
- Use valid JSON when the source is JSON
- Use valid YAML when the source is YAML

## Constraints

### Edge Cases

- If the card is partially valid but field names reflect a legacy or custom schema, distinguish `non-standard` from `invalid`.
- If two skills overlap heavily, call out the overlap as a routing risk even if the schema is valid.
- If the manifest includes extensions or custom metadata, keep them unless they create ambiguity or contradict published fields.
- If the user asks for a strict protocol audit only, skip heuristic rewrites.
- If the user asks for a rewrite only, still mention any protocol failures before presenting corrected text.

### Default Review Posture

- Be strict on schema facts
- Be explicit about uncertainty
- Be conservative in rewrites
- Separate fact from judgment
- Optimize for a router that must choose correctly among neighboring agents

### Execution Rules

- Do not report a heuristic issue as a protocol failure.
- Do not invent protocol requirements that are not supported by the source of truth.
- Do not rewrite valid custom fields unless they conflict with the protocol or the user explicitly asks for normalization.
- If the source manifest is partial, say so and limit conclusions to the visible fields.

## Post-Audit Confirmation

After presenting the full audit output:

1. Ask the user: *"Do you agree with the findings and the revised AgentCard above? If so, I can save it as a versioned file."*
2. If the user confirms:
   - Determine the source file path, the source manifest format, and a short agent identifier from the audit (e.g. `cbp` for the Configuration Best Practices agent). If the short identifier cannot be confidently derived from the card's name or context, ask the user before proceeding.
   - Use the naming pattern `agent_card_<agent>_vN.<ext>` where `<agent>` is the short identifier.
   - Inspect the target directory for existing versioned manifest files matching `agent_card_<agent>_v*.<ext>`.
   - Increment N to the next available version (start at `_v1` if none exist).
   - Create a new file at `agent_card_<agent>_vN.<ext>` containing only the revised AgentCard from the `### 5. Revised AgentCard` section.
   - Create the analysis file at `agent_card_<agent>_vN_analysis.md` containing the complete audit output except the full revised manifest body.
   - For the analysis file, use `_v0_analysis.md` if no prior versioned manifest files existed; otherwise use the same N as the revised manifest file.
3. If the user disagrees or requests changes, incorporate their feedback and re-run the affected audit checks before presenting a revised output.