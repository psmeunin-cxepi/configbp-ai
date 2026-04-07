# Agent Card Audit — Semantic Router Prompt

## Evaluation Criteria

Each agent card is evaluated against these best practices:

| # | Criterion | Description |
|---|-----------|-------------|
| C1 | **Compact card** | Short top-level description (1-2 sentences). No schema-level enumerations, no embedded specs. |
| C2 | **Explicit fields** | Clear name, focused description, skills with meaningful tags. No ambiguous or internal-label fields. |
| C3 | **Distinct skills** | Skills are non-overlapping within the agent and across agents. Each skill has a clear, unique intent. |
| C4 | **Model instruction** | Card includes or enables a short hint on *when to route here* (positive signal) vs burying routing logic in prose. |
| C5 | **Short, accurate description** (A2A) | Description captures the agent's core capability in one discriminative sentence — not a capability inventory. |
| C6 | **Sharply defined skills** (A2A) | Small number of skills with clear boundaries. Skill descriptions are intent-oriented, not implementation docs. |
| C7 | **Good tags** (A2A) | Tags are user-intent keywords (what a user would say), not internal system labels. |
| C8 | **Verbose detail moved out** (A2A) | Schema-level detail, input/output formats, filter dimension inventories, and routing instructions are NOT in the card. |

**Rating scale:** PASS · PARTIAL · FAIL

---

## Agent-by-Agent Evaluation

---

### 1. Product Recommendation

**Description word count:** ~8 words
**Skills:** 1
**Tags:** [recommendation]

| Criterion | Rating | Notes |
|-----------|--------|-------|
| C1 Compact | PASS | Very short description. |
| C2 Explicit fields | PARTIAL | Name and description are clear. Tags are too sparse — only `[recommendation]` gives the router very little signal. |
| C3 Distinct skills | PARTIAL | Skill description repeats the agent description almost verbatim, then adds "answers energy related questions about products, gives recommendations based on energy related parameters" — this energy-specific detail is oddly narrow and could confuse routing for non-energy questions. |
| C4 Model instruction | FAIL | No positive routing signal beyond the generic description. No "route here when..." hint. |
| C5 Short description | PASS | One sentence, accurate. |
| C6 Sharply defined skills | PARTIAL | Single skill is fine, but its description mixes general product recommendation with a niche energy sub-domain. |
| C7 Good tags | FAIL | `[recommendation]` alone is too vague. Missing obvious intent keywords: `product`, `replacement`, `alternative`, `upgrade`, `suggest`. |
| C8 Verbose detail out | PASS | No excess detail. |

**Key issues:**
- Tags are nearly useless for routing — add intent-level keywords.
- The energy-related detail in the skill description is either core (in which case the agent description should mention it) or niche (in which case it shouldn't dominate the only skill's description).

---

### 2. Peer Benchmark Analysis

**Description word count:** ~130 words
**Skills:** 1
**Tags:** [peer_benchmark, static, iq_external, kpi, comparison]

| Criterion | Rating | Notes |
|-----------|--------|-------|
| C1 Compact | FAIL | ~130-word description enumerates every supported metric type (PSIRT exposure, FN age buckets, LDOS time ranges). This is a spec, not a card. |
| C2 Explicit fields | PARTIAL | Name is clear. Description doubles as a specification document. |
| C3 Distinct skills | PASS | Single skill, clear domain. |
| C4 Model instruction | PARTIAL | "Only topics that help users understand how their Cisco asset management compares to industry peers are considered valid" at the end acts as a routing instruction, but it's buried after a wall of detail. |
| C5 Short description | FAIL | Should be: "Compares a customer's asset metrics (LDOS, PSIRT, FN, telemetry) against peer group averages and percentiles." The current version lists every metric sub-type. |
| C6 Sharply defined skills | PARTIAL | Skill description is also long and overlaps with the agent description. |
| C7 Good tags | FAIL | `static` and `iq_external` are internal system labels — they carry zero intent signal for routing. `peer_benchmark`, `kpi`, `comparison` are okay. |
| C8 Verbose detail out | FAIL | Age bucket breakdowns (<30d, 30-60d, 60-90d, >90d), LDOS time ranges (0-6m, 6-12m, 12-24m, 24m+), and metric sub-type enumerations should be in an extended card or docs. |

**Key issues:**
- Description is 10x longer than needed. The router only needs to know: "peer group comparison of asset metrics."
- Internal tags (`static`, `iq_external`) pollute the tag set.
- Domain overlap with Assets (General) on LDOS terms — the description doesn't make it clear when a user asking about LDOS should come here vs. the LDOS agent.

---

### 3. Troubleshooting

**Description word count:** ~150 words
**Skills:** 4 (cx_ai_fn_q_a, get_cve_details, ciscoiq_get_asset, ciscoiq_search_assets)
**Tags:** NONE on any skill

| Criterion | Rating | Notes |
|-----------|--------|-------|
| C1 Compact | FAIL | Description has two bullet lists (capabilities + routing instructions), with redundant entries. |
| C2 Explicit fields | FAIL | No tags on any skill. Skill names use internal prefixes (`cx_ai_`, `ciscoiq_`). |
| C3 Distinct skills | FAIL | `ciscoiq_get_asset` and `ciscoiq_search_assets` are asset-lookup tools that overlap with the Assets (General) agent. A user asking "look up serial number X" could match either agent. Also, `cx_ai_fn_q_a` (field notices) overlaps with the Cases agent topic area. |
| C4 Model instruction | PARTIAL | "Send user message here, if the user provides: ..." acts as a routing instruction, but it's an afterthought appended to the capabilities list. |
| C5 Short description | FAIL | Starts with informal grammar ("This is a troubleshooting assistant it can do the following"). Should be: "Diagnoses device issues using logs, syslogs, crash dumps, and Cisco documentation. Looks up CVEs, field notices, and bug IDs." |
| C6 Sharply defined skills | FAIL | `get_cve_details` has a 100+ word description including input format specs ("The task expects an input of the following format..."), output format, and behavioral instructions ("ALWAYS include the product and software"). This is executor-level documentation, not routing info. |
| C7 Good tags | FAIL | Zero tags on all 4 skills. |
| C8 Verbose detail out | FAIL | Input/output format specs for `get_cve_details`, return field enumerations for `ciscoiq_get_asset` and `ciscoiq_search_assets` — all should be in skill-executor docs, not the routing card. |

**Key issues:**
- Worst offender for mixing routing info with implementation detail.
- Redundant bullets: "answer questions about logs, error messages" appears in two slightly different forms.
- Asset-lookup skills (`ciscoiq_get_asset`, `ciscoiq_search_assets`) create direct routing confusion with Assets (General) agent.
- Zero tags makes keyword-based routing impossible.

---

### 4. Cases

**Description word count:** ~60 words
**Skills:** 6 (csf_ai_get_case_details, cx_ai_list_cases, caia_generate_summary, buff_mcp, copilot_auto_close, add_note_to_case)
**Tags:** NONE on any skill

| Criterion | Rating | Notes |
|-----------|--------|-------|
| C1 Compact | PARTIAL | Description is moderate length but opens with "tac assistant for cvi integration" — internal jargon. |
| C2 Explicit fields | FAIL | No tags on any skill. Internal acronyms in description ("cvi"). |
| C3 Distinct skills | FAIL | `buff_mcp` description says "list cases" — directly overlaps with `cx_ai_list_cases`. Unclear when to use which. |
| C4 Model instruction | PARTIAL | "This assistant cannot troubleshoot customer issues" is a useful negative boundary but is embedded mid-paragraph. |
| C5 Short description | PARTIAL | Core idea is clear (case management) but the opening sentence is implementation-focused. Should be: "Manages Cisco TAC support cases: list, view, summarize, create, escalate, close, and update cases." |
| C6 Sharply defined skills | FAIL | `copilot_auto_close` includes a user-facing instruction ("Tell the end user the case will be queued for closure and will be closed in 5-10 minutes") — this is runtime behavior, not routing info. `csf_ai_get_case_details` describes the return dict structure. `buff_mcp` is vaguely described. |
| C7 Good tags | FAIL | Zero tags on all 6 skills. |
| C8 Verbose detail out | PARTIAL | Return format of `csf_ai_get_case_details` and user-facing script in `copilot_auto_close` should be in executor docs. |

**Key issues:**
- "This Assistant can also answer questions related to software bugs" creates overlap with Troubleshooting agent which also lists software bugs.
- `buff_mcp` is a vague catch-all that partially duplicates other skills in the same agent.
- 6 skills with no tags is a routing black hole — the router has to rely entirely on description matching.

---

### 5. Assessments – Configuration

**Description word count:** ~80 words
**Skills:** 4 (assessments-configuration-summary, asset-scope-analysis, rule-analysis, signature-asset-insights)
**Tags:** YES — extensive (12, 16, 11, 7 tags respectively)

| Criterion | Rating | Notes |
|-----------|--------|-------|
| C1 Compact | PARTIAL | Description is a structured capability inventory mapping 4 numbered items to 4 skills. Acceptable structure but still 80 words. |
| C2 Explicit fields | PASS | Clear name, structured description, all skills have tags. |
| C3 Distinct skills | PASS | 4 skills cover distinct angles: summary, asset-scoped, rule-centric, AI insights. Well-partitioned. |
| C4 Model instruction | FAIL | No routing signal or boundary statement. Router must infer entirely from description overlap with user queries. |
| C5 Short description | PARTIAL | Could be shorter: "Analyzes network configuration against best practice rules; surfaces violations, severity, impact, and remediation." The current description redundantly previews each skill. |
| C6 Sharply defined skills | PARTIAL | Skill descriptions are 50-80 words each. `asset-scope-analysis` lists 20+ filterable dimensions — this is schema detail. |
| C7 Good tags | PARTIAL | Many intent-relevant tags (assessment, summary, severity, rule, compliance), but also generic ones (filter, scope, impact) and the tag `lifecycle` on `asset-scope-analysis` which causes documented routing confusion with LDOS agent. |
| C8 Verbose detail out | FAIL | `asset-scope-analysis` enumerates 20+ filter dimensions (hostname, IP, product family, product type, asset type, location, software type and version, contract number, coverage status, support type, telemetry status, data source, partner name, entitlement level, role, lifecycle milestones, date-range). This is a schema spec. |

**Key issues:**
- `lifecycle` tag on `asset-scope-analysis` is a known routing hazard — it's a filter dimension, not the agent's purpose, but the tag makes it a false positive for lifecycle questions.
- Skill descriptions double as API documentation; filter dimensions should be moved out.
- Best-structured card of the set, but still too verbose.

---

### 6. Assessments – Health Risk Insights

**Description word count:** ~40 words
**Skills:** 2 (health-risk-analysis-query, health-risk-individual-rating-query)
**Tags:** YES — 5 tags each

| Criterion | Rating | Notes |
|-----------|--------|-------|
| C1 Compact | PASS | Moderate length, manageable. |
| C2 Explicit fields | PASS | Clear name, focused description, tags present. |
| C3 Distinct skills | PASS | Two skills cleanly split: fleet-wide analysis vs. individual device. |
| C4 Model instruction | FAIL | No routing hint. The word "risk" appears heavily but is also used by Asset Criticality and Security agents — no disambiguation guidance. |
| C5 Short description | PARTIAL | "An intelligent AI agent specializing in..." is filler. Should be: "Analyzes Cisco Health Risk Scores: fleet-wide risk categorization and individual asset risk breakdowns." |
| C6 Sharply defined skills | PASS | Clean split between aggregate and individual. |
| C7 Good tags | PARTIAL | `cisco-health-risk` is brand-specific noise. `health-risk`, `risk-score`, `risk-analysis` are useful. `individual-asset` and `risk-detail` are good differentiators. |
| C8 Verbose detail out | PASS | No excessive detail. |

**Key issues:**
- "risk" term saturation: This agent, Asset Criticality, and Security Advisories all claim "risk" — the card does nothing to help the router disambiguate.
- Filler opening ("An intelligent AI agent specializing in") wastes tokens.
- Overall one of the better cards — relatively clean and compact.

---

### 7. Assessments – Security Hardening

**Description word count:** ~45 words
**Skills:** 1
**Tags:** [security_hardening, best_practices, hardening, baseline, compliance]

| Criterion | Rating | Notes |
|-----------|--------|-------|
| C1 Compact | PASS | Short and focused. |
| C2 Explicit fields | PASS | Clear name, tags present. |
| C3 Distinct skills | PARTIAL | Single skill, but its domain ("security hardening best practices and device compliance") overlaps with Security Advisories agent which also lists "Security Hardening" as a sub-topic. |
| C4 Model instruction | PARTIAL | Opens with "Questions and content must be directly related to..." — functions as a routing gate but is phrased prescriptively. |
| C5 Short description | PARTIAL | The opening sentence is a routing instruction, not a description. Core description is in the bold sub-sections. Should lead with: "Provides Cisco security hardening recommendations, baseline configurations, and compliance guidance for IOS/IOS XE/NX-OS." |
| C6 Sharply defined skills | PASS | Single skill, clear intent. |
| C7 Good tags | PASS | Tags are intent-relevant: a user would say "hardening", "baseline", "compliance". |
| C8 Verbose detail out | PASS | No excess. |

**Key issues:**
- Cross-agent overlap: Security Advisories agent lists "Security Hardening: Questions related to security hardening best practices and device compliance" as one of its sub-topics. This means a hardening question matches BOTH agents' descriptions. This should be resolved in one place — either remove hardening from Security Advisories or merge the agents.
- Description opens with a routing instruction instead of describing what the agent does.

---

### 8. Assessments – Security Advisories

**Description word count:** ~70 words
**Skills:** 1
**Tags:** [security_assessment, psirt, vulnerability, risk, telemetry]

| Criterion | Rating | Notes |
|-----------|--------|-------|
| C1 Compact | PARTIAL | Moderate length. |
| C2 Explicit fields | PASS | Clear name, tags present. |
| C3 Distinct skills | FAIL | Description lists "Security Hardening" as a sub-topic, directly overlapping with the dedicated Security Hardening agent. Also claims "Risk Analysis" which overlaps with Health Risk Insights and Asset Criticality. |
| C4 Model instruction | PARTIAL | Opens with "Questions and content must be directly related to..." — same pattern as Security Hardening. |
| C5 Short description | PARTIAL | Like Security Hardening, the opening sentence is a routing instruction. Should be: "Analyzes device vulnerability exposure to Cisco PSIRTs and security advisories across the fleet." |
| C6 Sharply defined skills | PARTIAL | Single skill is fine, but its description says "security hardening best practices" which duplicates the other agent's entire domain. |
| C7 Good tags | PARTIAL | `psirt`, `vulnerability` are good. `risk` is overloaded (shared with 3+ agents). `telemetry` is a secondary concern that could attract false positives. |
| C8 Verbose detail out | PASS | Not excessively verbose. |

**Key issues:**
- Encroaches on Security Hardening agent's territory by listing it as a sub-topic.
- `risk` tag shared with Health Risk Insights and Asset Criticality — no disambiguation.
- "Device Telemetry" sub-topic is weakly related and could attract telemetry-focused questions that belong to Assets (General).

---

### 9. Assets (General)

**Description word count:** ~400 words
**Skills:** 1
**Tags:** [sav_id, ldos, iq_external]

| Criterion | Rating | Notes |
|-----------|--------|-------|
| C1 Compact | FAIL | By far the longest card at ~400 words. Contains multiple sections: SUPPORTED DATA DOMAINS (8 bullets), SUPPORTED QUERY TYPES (5 bullets), ALSO ROUTE THESE HERE (3 bullets), DO NOT ROUTE HERE (6 bullets). |
| C2 Explicit fields | FAIL | Tags are internal implementation labels: `sav_id`, `iq_external` — meaningless for routing. |
| C3 Distinct skills | PARTIAL | Single skill covers a very broad domain. The skill name `ask_cvi_ldos_ai_external` uses internal labels and emphasizes "LDOS" despite the agent covering much more than lifecycle. |
| C4 Model instruction | PARTIAL | Has explicit ALSO ROUTE / DO NOT ROUTE sections, but these are router-level instructions embedded in the card — they should be in the Routing Overrides section of the prompt. |
| C5 Short description | FAIL | First sentence is fine: "This agent answers questions about a customer's Cisco network assets and inventory data." Everything after is a specification document. |
| C6 Sharply defined skills | FAIL | Single skill covers 8 data domains — it's a catch-all. Name includes internal labels. |
| C7 Good tags | FAIL | `sav_id` and `iq_external` are internal implementation identifiers. `ldos` is relevant but the agent handles far more than LDOS. Missing: `inventory`, `assets`, `contract`, `coverage`, `telemetry`, `location`, `lifecycle`, `tags`. |
| C8 Verbose detail out | FAIL | The entire SUPPORTED DATA DOMAINS section is a database schema description. Filter enumerations (equipment types, contract types like SNC/SSSNT/SNT, entitlement levels), pricing fields, and tag Key:Value format specs should all be in docs. |

**Key issues:**
- This is a specification document, not a card. It's 50x the recommended size.
- Tags are actively harmful — `sav_id` and `iq_external` are noise that dilutes routing signal.
- ALSO ROUTE / DO NOT ROUTE sections are router instructions that belong in the Routing Overrides section, not inside the card.
- Skill name `ask_cvi_ldos_ai_external` is misleading — "LDOS" in the name suggests lifecycle-only, but the agent covers inventory, contracts, telemetry, tags, pricing, and more.
- The DO NOT ROUTE section (~6 bullets) uses card real estate for negative information — the router has to process what the agent DOESN'T do.

---

### 10. Asset Criticality

**Description word count:** ~250 words
**Skills:** 1
**Tags:** [ldos, criticality, pin, psirt, field_notices, prioritization]

| Criterion | Rating | Notes |
|-----------|--------|-------|
| C1 Compact | FAIL | ~250 words with same spec-document structure as Assets (General): SUPPORTED DATA DOMAINS, SUPPORTED QUERY TYPES, ALSO ROUTE, DO NOT ROUTE. |
| C2 Explicit fields | PARTIAL | Tags are better than Assets (General) but include `ldos` and `psirt` which are primary domains of other agents. |
| C3 Distinct skills | PARTIAL | Single skill, clear core domain (criticality/PIN), but tags and description claim LDOS, PSIRT, and field notices as sub-domains — treading on 3 other agents' territory. |
| C4 Model instruction | PARTIAL | Has ALSO ROUTE / DO NOT ROUTE sections. Same issue: router instructions embedded in card. |
| C5 Short description | PARTIAL | Opening sentence is good: "This agent answers questions about asset risk, criticality, and prioritization for a customer's Cisco network devices." The rest is a spec. |
| C6 Sharply defined skills | PARTIAL | Single skill covers a focused domain, but its tag set (`ldos`, `psirt`, `field_notices`) imports other agents' primary keywords. |
| C7 Good tags | PARTIAL | `criticality`, `pin`, `prioritization` are unique and useful. `ldos`, `psirt`, `field_notices` create overlap with other agents. |
| C8 Verbose detail out | FAIL | DO NOT ROUTE section is nearly identical to Assets (General)'s — duplicated boilerplate. SUPPORTED DATA DOMAINS enumerates sub-domains at schema level. |

**Key issues:**
- DO NOT ROUTE section is copy-pasted from Assets (General) — 5 of 6 bullets are identical.
- Tags import primary keywords from other agents (`ldos` from Assets, `psirt` from Security Advisories, `field_notices` from Troubleshooting).
- The card doesn't make clear that this agent is the *intersection* of criticality with those domains, not a replacement for them.

---

## Cross-Agent Issues

### 1. Term Overloading — "risk"
The word "risk" appears prominently in **4 agents**: Health Risk Insights, Asset Criticality, Security Advisories, and Peer Benchmark Analysis. None of the cards disambiguate which kind of risk they handle. The router must rely on the Routing Overrides section to sort this out.

| Agent | What "risk" means here |
|-------|----------------------|
| Health Risk Insights | Cisco Health Risk Score (composite compliance score) |
| Asset Criticality | Prioritization risk (PIN importance × exposure) |
| Security Advisories | Vulnerability exposure risk (PSIRTs) |
| Peer Benchmark | Comparative risk posture vs. peers |

**Recommendation:** Each card should qualify "risk" with its specific meaning in the description or tags.

### 2. Term Overloading — "lifecycle" / "LDOS"
`lifecycle` and `ldos` appear in Assets (General), Asset Criticality, Assessments – Configuration (as a tag), and Peer Benchmark Analysis. Only Assets (General) is the dedicated lifecycle agent, but the tag presence on other agents creates false positives.

### 3. Embedded Routing Instructions
Three agents (Assets General, Asset Criticality, Security Hardening/Advisories) put routing instructions inside their cards (ALSO ROUTE HERE, DO NOT ROUTE HERE, "Questions must be directly related to..."). These are router-level concerns that belong in the Routing Overrides/Instructions section. Embedding them in cards:
- Inflates card size
- Mixes concerns (agent capability vs. routing policy)
- Creates maintenance burden (changes in routing logic require editing individual cards)

### 4. Internal Labels in Tags and Skill Names
| Label | Where | Problem |
|-------|-------|---------|
| `sav_id` | Assets (General) tag | Internal DB identifier — no routing value |
| `iq_external` | Assets (General) + Peer Benchmark tag | Internal system flag — no routing value |
| `static` | Peer Benchmark tag | Internal data-source flag |
| `cvi` | Cases description, skill name `ask_cvi_ldos_ai_external` | Internal product acronym |
| `cx_ai_`, `csf_ai_`, `ciscoiq_` | Multiple skill name prefixes | Internal team/system prefixes |

### 5. Skill Overlap Across Agents
| Skill A (Agent) | Skill B (Agent) | Overlap |
|-----------------|-----------------|---------|
| `ciscoiq_get_asset` (Troubleshooting) | `ask_cvi_ldos_ai_external` (Assets General) | Both look up asset info by serial number |
| `ciscoiq_search_assets` (Troubleshooting) | `ask_cvi_ldos_ai_external` (Assets General) | Both search assets by name/family/software |
| `cx_ai_fn_q_a` (Troubleshooting) | `ask_security_assessment` (Security Advisories) | Both handle field notice questions |
| `buff_mcp` list-cases (Cases) | `cx_ai_list_cases` (Cases) | Same function within same agent |
| Security Hardening sub-topic (Security Advisories) | `ask_security_hardening` (Security Hardening) | Same domain claimed by two agents |

### 6. Missing Tags
| Agent | Skills with zero tags |
|-------|-----------------------|
| Troubleshooting | All 4 skills |
| Cases | All 6 skills |

These 10 skills (out of 25 total) have no tags at all — 40% of skills are invisible to tag-based matching.

---

## Summary Scorecard

| Agent | C1 Compact | C2 Explicit | C3 Distinct | C4 Instruction | C5 Short Desc | C6 Sharp Skills | C7 Tags | C8 Detail Out | Score |
|-------|:----------:|:-----------:|:-----------:|:--------------:|:-------------:|:---------------:|:-------:|:-------------:|:-----:|
| Product Recommendation | PASS | PARTIAL | PARTIAL | FAIL | PASS | PARTIAL | FAIL | PASS | 4/8 |
| Peer Benchmark | FAIL | PARTIAL | PASS | PARTIAL | FAIL | PARTIAL | FAIL | FAIL | 2/8 |
| Troubleshooting | FAIL | FAIL | FAIL | PARTIAL | FAIL | FAIL | FAIL | FAIL | 0.5/8 |
| Cases | PARTIAL | FAIL | FAIL | PARTIAL | PARTIAL | FAIL | FAIL | PARTIAL | 1.5/8 |
| Assessments – Config | PARTIAL | PASS | PASS | FAIL | PARTIAL | PARTIAL | PARTIAL | FAIL | 3.5/8 |
| Assessments – Health Risk | PASS | PASS | PASS | FAIL | PARTIAL | PASS | PARTIAL | PASS | 5.5/8 |
| Security Hardening | PASS | PASS | PARTIAL | PARTIAL | PARTIAL | PASS | PASS | PASS | 6/8 |
| Security Advisories | PARTIAL | PASS | FAIL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PASS | 4/8 |
| Assets (General) | FAIL | FAIL | PARTIAL | PARTIAL | FAIL | FAIL | FAIL | FAIL | 1/8 |
| Asset Criticality | FAIL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | FAIL | 2/8 |

*(PASS = 1, PARTIAL = 0.5, FAIL = 0)*

### Ranking by Quality

1. **Security Hardening** — 6/8 — Compact, good tags, clear domain. Fix: remove routing instruction phrasing from description; resolve overlap with Security Advisories.
2. **Health Risk Insights** — 5.5/8 — Clean structure, good skill split. Fix: remove filler opening; qualify "risk" type; add routing hint.
3. **Product Recommendation** — 4/8 — Very compact but under-specified. Fix: add tags; clarify energy sub-domain; add routing hint.
4. **Security Advisories** — 4/8 — Reasonable structure. Fix: remove hardening sub-topic (belongs to other agent); disambiguate "risk".
5. **Assessments – Config** — 3.5/8 — Best skill partitioning. Fix: remove filter dimension enumerations; remove `lifecycle` tag; shorten skill descriptions.
6. **Peer Benchmark** — 2/8 — Good domain but over-documented. Fix: cut description to 2 sentences; remove internal tags.
7. **Asset Criticality** — 2/8 — Clear core domain buried under spec boilerplate. Fix: remove embedded routing instructions; qualify shared tags.
8. **Cases** — 1.5/8 — Functional domain, poor card design. Fix: add tags; resolve internal skill overlap; remove implementation details from skill descriptions.
9. **Assets (General)** — 1/8 — Specification document, not a card. Fix: cut to 2 sentences; replace internal tags; move data domain specs to docs.
10. **Troubleshooting** — 0.5/8 — Worst card. Fix: rewrite description; add tags to all skills; remove asset-lookup skills or clarify boundary with Assets agent; remove input/output format specs from skills.

---

## Recommended Next Steps

1. **Rewrite all descriptions** to 1-2 discriminative sentences. Move capability inventories, data domain specs, and filter enumerations to a separate reference document.
2. **Extract routing instructions** from cards. Move all ALSO ROUTE / DO NOT ROUTE / "must be directly related to" clauses to the Routing Overrides section where they belong.
3. **Add tags to all skills** — especially Troubleshooting (4 skills) and Cases (6 skills). Use intent-level keywords a user would say, not internal system labels.
4. **Remove internal labels** from tags: `sav_id`, `iq_external`, `static`, `cvi`.
5. **Resolve cross-agent overlaps**: Security Hardening vs. Security Advisories, Troubleshooting asset tools vs. Assets (General), `buff_mcp` vs. `cx_ai_list_cases`.
6. **Disambiguate shared terms** — add a qualifier to "risk", "lifecycle", and "support" in each card that uses them.
7. **Remove implementation detail** from skill descriptions — input formats, return dict structures, and user-facing scripts belong in executor docs.
8. **Add a 1-line routing hint** to each card: "Route here when the user asks about [X]. Do not route here for [Y]." — keep it to a single sentence.
