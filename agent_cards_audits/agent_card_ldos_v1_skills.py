from a2a.types import AgentSkill

ASSETS_GENERAL_QUESTIONS = [
    "How many unique devices are there?",
    "How many sub-components are reaching LDOS in the next 12 months?",
    "Count assets by coverage status.",
    "Count assets by telemetry status.",
    "What devices have the tag Status:Covered?",
    "Which software type contains the greatest number of assets?",
    "Which data source has the most assets with high or critical vulnerabilities?",
    "Find all assets with extended support currently in effect.",
]

INTERNAL_STATIC_QUESTIONS = [
    "Summarize assets past Last Date of Support (LDOS) in the last 12 months.",
    "Summarize assets past Last Date of Support (LDOS).",
    "Summarize assets reaching Last Date of Support (LDOS) in the next 12 months.",
    "Summarize assets past Last Date of Support (LDOS) by opportunity size using Product Net Price.",
    "Generate a PPT summary report for all Last Date of Support (LDOS) assets.",
] + ASSETS_GENERAL_QUESTIONS

EXTERNAL_STATIC_QUESTIONS = [
    "Summarize assets past Last Date of Support (LDOS) in the last 12 months.",
    "Summarize assets past Last Date of Support (LDOS).",
    "Summarize assets reaching Last Date of Support (LDOS) in the next 12 months.",
    "Generate a PPT summary report for all Last Date of Support (LDOS) assets.",
    "Which product families have the most assets past Last Date of Support (LDOS)?",
    "Which locations have the most assets past Last Date of Support (LDOS)?",
    "In the next 12 months, which product families will have the most assets past Last Date of Support (LDOS)?",
    "In the next 12 months, which locations will have the most assets past Last Date of Support (LDOS)?",
] + ASSETS_GENERAL_QUESTIONS

ASSET_CRITICALITY_QUESTIONS = [
    "What are my most critical assets by role and importance?",
    "Which assets past their last date of support should I refresh first based on their importance?",
    "Which three product families have the most devices that are both end-of-life and have active security vulnerabilities?",
    "Prioritize which field notices to address first based on device importance.",
    "How many devices have field notices?",
    "How many of my core devices have high or critical security advisories?",
    "Show me high importance devices that are not covered.",
    "How many devices have both security advisories and field notices?",
]

ask_cvi_ldos_ai_internal = AgentSkill(
    id="asset-lifecycle-internal",
    name="Asset Lifecycle Analysis (Internal)",
    description=(
        "Provides Cisco-internal lifecycle intelligence and general asset inventory "
        "analysis — LDOS/end-of-life milestones, device counts, coverage and telemetry "
        "status, tags, sub-components, location breakdowns, and internal-only metrics "
        "such as PSIRT mappings and net-price opportunity sizing."
    ),
    tags=[
        "asset-inventory",
        "lifecycle",
        "ldos",
        "end-of-life",
        "coverage",
        "telemetry",
        "contract",
        "tags",
        "location",
        "internal",
    ],
    examples=INTERNAL_STATIC_QUESTIONS,
)

ask_cvi_ldos_ai_external = AgentSkill(
    id="asset-lifecycle-external",
    name="Asset Lifecycle Analysis",
    description=(
        "Answers customer-facing questions about Cisco product lifecycle data and "
        "asset inventory — LDOS/end-of-life milestones, connectivity and telemetry "
        "status, asset summaries, coverage/contract details, tags, sub-components, "
        "and location analysis using customer-authorized data."
    ),
    tags=[
        "asset-inventory",
        "lifecycle",
        "ldos",
        "end-of-life",
        "coverage",
        "telemetry",
        "contract",
        "tags",
        "location",
        "customer-facing",
    ],
    examples=EXTERNAL_STATIC_QUESTIONS,
)

ask_asset_criticality = AgentSkill(
    id="asset-criticality",
    name="Asset Criticality & Risk Prioritization",
    description=(
        "Answers questions about asset risk, criticality, and prioritization — "
        "Place in Network (PIN) role and importance, security advisory severity "
        "correlated with device importance, field notice prioritization, and "
        "refresh/coverage recommendations based on combined risk signals."
    ),
    tags=[
        "criticality",
        "pin",
        "place-in-network",
        "psirt",
        "field-notices",
        "prioritization",
        "risk-ranking",
        "refresh",
        "security-advisory",
    ],
    examples=ASSET_CRITICALITY_QUESTIONS,
)
