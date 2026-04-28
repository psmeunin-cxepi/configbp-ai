# Semantic Overlap Audit

Use this reference when the task is not only to improve a single AgentCard, but to determine whether one card or skill is semantically too close to other cards in the workspace and may create routing ambiguity.

## Purpose

Semantic overlap means a router could plausibly select more than one card or skill for the same request because their routing signals are too similar.

This audit is not limited to a single field. Compare every signal that materially affects routing quality, including:

- `AgentCard.description`
- `AgentSkill.description`
- `AgentSkill.tags`
- `AgentSkill.examples`
- terminology consistency across the card
- whether implementation detail dilutes the routing boundary
- explicit and implicit scope constraints such as audience, geography, auth boundary, system boundary, artifact type, lifecycle stage, and trigger conditions

## When To Use

Use this reference when the user asks to:

- compare one card against other cards in the workspace
- detect overlap, duplication, or routing ambiguity across agents
- identify collisions between skills owned by different cards
- narrow boundaries between nearby cards or skills

Do not use this reference for a single-card quality review unless cross-registry ambiguity is part of the task.

## Unit Of Analysis

Evaluate semantic overlap at both levels:

- `AgentCard`
- `AgentSkill`

Do not assume one level is the default comparison unit. Use the level or levels required by the audit request and report clearly whether the finding is card-level, skill-level, or both.

## Comparison Scope

When comparing a candidate against existing workspace manifests, evaluate all routing-quality signals together rather than scoring each field in isolation.

The comparison must explicitly cover all of these routing fields:

1. `AgentCard.description`
2. `AgentSkill.description`
3. `AgentSkill.tags`
4. `AgentSkill.examples`

In addition, compare these cross-field routing signals:

5. Distinguishing constraints
6. Terminology consistency
7. Boundary clarity

### 1. `AgentCard.description`

Compare whether the candidate card description and the nearest neighbor card description point to the same overall agent purpose, lane, and routing boundary.

### 2. `AgentSkill.description`

Compare whether the candidate and the nearest neighbor express the same:

- action
- object or entity
- intended outcome

### 3. `AgentSkill.tags`

Compare whether the tags point to the same likely user phrasing, capability cues, and domain vocabulary.

### 4. `AgentSkill.examples`

Compare whether their examples would attract the same user requests or scenarios.

### 5. Distinguishing constraints

Look for boundaries that reduce overlap, such as:

- audience or role
- geography or region
- source system
- auth or permission boundary
- artifact type or format
- workflow stage or lifecycle stage
- trigger condition
- escalation or ownership boundary

### 6. Terminology consistency

Check whether different cards use near-synonyms for the same behavior, which can make them appear more overlapping than intended.

### 7. Boundary clarity

Check whether implementation detail or broad marketing language weakens the practical routing boundary.

## Candidate Selection

Do not compare every card to every other card blindly.

For the candidate under review:

1. Extract the main card purpose, action, entity, outcome, and key vocabulary from the candidate.
2. Find the top 3 nearest comparison targets in the workspace.
3. Compare the candidate against each selected neighbor across all required routing fields listed in `## Comparison Scope`.
4. Score only those nearest neighbors unless the user explicitly asks for exhaustive pairwise comparison.

Nearest comparison targets should be selected using overlap in card descriptions, skill descriptions, tags, examples, and shared domain terms.

## Overlap Rubric

Use the following bands as calibration anchors. If you provide a numeric estimate, it must support the selected band rather than replace it.

| Band | Approximate Range | Semantic State | Audit Requirement |
|---|---|---|---|
| `Distinct` | 0-25 | Different intent, different object, or different success condition | `PASS` |
| `Adjacent` | 26-50 | Shared domain vocabulary but different user goal or boundary | `PASS` or `WARN` if wording is vague |
| `Overlapping` | 51-75 | Meaningful routing ambiguity unless boundaries are sharpened | `WARN` |
| `Collision` | 76-100 | Same or nearly same action, object, and outcome for realistic user requests | `FAIL` |

Do not treat the approximate range as a mathematically precise score. The band is primary. The number is optional and secondary.

## Evidence-First Method

Before assigning a band, produce explicit comparison evidence.

### Required evidence

1. **Nearest Neighbor**
   Name the closest collision partner.

2. **Shared Traits**
   List the important card-purpose cues, actions, entities, outcomes, tags, and example patterns they share.

3. **Distinguishing Traits**
   List the constraints that separate them, if any.

4. **Confusion Query**
   Write one realistic user query that would make routing ambiguous between the two.

5. **Band Decision**
   Assign `Distinct`, `Adjacent`, `Overlapping`, or `Collision` and justify it with the evidence above.

If you cannot identify a realistic confusion query, the pair is unlikely to be a true collision.

## Decision Rules

Use these rules when assigning the final band.

- If two candidates share the same card purpose, action, object, and outcome, and differ only in wording, treat this as `Collision`.
- If they share domain and vocabulary but differ by a meaningful operating boundary, treat this as `Adjacent` or `Overlapping` depending on how obvious that boundary is to a router.
- If the only differentiator is hidden in implementation detail, treat the pair as more overlapping than the authors intended.
- If tags and examples attract the same requests even when descriptions differ, weight the pair toward `Overlapping` or `Collision`.
- If card descriptions suggest the same agent lane even when individual skill wording differs, weight the pair toward `Overlapping` or `Collision`.
- If a boundary is present but weakly expressed, prefer `WARN` with a rewrite recommendation over a false `PASS`.

## Recommended Remediation

Do not prescribe repository policy unless the user asks for it. Default to audit recommendations.

### For `Adjacent`

- No mandatory rewrite
- Optionally improve wording if the boundary is real but understated

### For `Overlapping`

- Recommend a differentiator rewrite
- Tighten description, tags, and examples together
- Add or clarify a real boundary such as audience, geography, system, artifact, or workflow stage

### For `Collision`

- Recommend scope narrowing, consolidation review, or explicit ownership split
- Provide at least one concrete rewrite that reduces ambiguity
- If no meaningful differentiator exists, say so clearly

Do not use `Routing Hint` as the only fix. A hint may help, but it cannot compensate for fundamentally overlapping scope.

## Rewrite Guidance

When proposing a differentiator fix:

- Change the smallest set of fields that meaningfully improves routing separation
- Prefer real scope boundaries over cosmetic rewording
- Keep the rewrite consistent across `AgentCard.description`, `AgentSkill.description`, `AgentSkill.tags`, and `AgentSkill.examples`
- Do not invent capabilities or constraints that are unsupported by the source material

## Output Format

Use this structure for each reviewed candidate.

## Semantic Overlap Report: [Candidate Skill Or Agent]

| Candidate | Closest Neighbor | Band | Estimated Score | Result |
|---|---|---|---|---|
| [candidate] | [neighbor] | `Overlapping` | 64 | `WARN` |

### Shared Traits

- [shared action or outcome]
- [shared entity or request pattern]

### Distinguishing Traits

- [constraint or boundary]
- [constraint or boundary]

### Confusion Query

`[One realistic user request that could route to both]`

### Why This Band Applies

[Short evidence-based justification]

### Recommended Fix

- [specific rewrite or scope change]

## Constraints

- Do not score overlap from any single field alone.
- Do not skip any of the required routing fields in `## Comparison Scope` when they are present in both candidates.
- Do not use raw percentages without assigning a rubric band.
- Do not classify cards as duplicates unless the evidence shows the same routing intent in practice.
- Do not recommend deletion by default; recommend consolidation review instead.
- If the workspace sample is incomplete, say so and limit the confidence of the conclusion.