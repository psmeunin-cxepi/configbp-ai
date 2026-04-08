import os
from a2a.types import AgentCard, AgentCapabilities, AgentInterface, AgentSkill

A2A_SERVER_URL = os.getenv("A2A_SERVER_URL", "http://localhost:9000")

AGENT_CARD = AgentCard(
    name="Assessments – Configuration",
    version="1.0.0",
    description=(
        "Analyzes a customer's network configuration against best practice rules, "
        "surfaces violations with severity and impact, and recommends remediation. "
        "Route here when the user asks about configuration assessments, deviations, "
        "or best practice compliance—not for software, security, or lifecycle assessments."
    ),
    supported_interfaces=[
        AgentInterface(
            url=A2A_SERVER_URL,
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        )
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(
        streaming=True,
        push_notifications=False,
    ),
    skills=[
        AgentSkill(
            id="assessments-configuration-summary",
            name="Assessments Configuration Summary",
            description=(
                "Returns an aggregate overview of a configuration assessment: "
                "total assets evaluated, violation counts by severity, pass/fail "
                "rates, and breakdowns by technology and category. Answers broad "
                "posture questions, not per-device drill-downs."
            ),
            tags=[
                "assessment",
                "summary",
                "severity",
                "overview",
                "distribution",
                "metrics",
                "technology",
                "violations",
                "pass-fail",
                "category",
                "trends",
            ],
            examples=[
                "Can you provide a summary of my recent Configuration Assessment?",
                "How many best practice rules were evaluated, and how many had at least one failing asset?",
                "What are the most common configuration deviations across my network?",
                "How many assets were evaluated, and what percentage did not pass?",
                "Which categories have the most deviations from best practices?",
                "Show breakdown of deviations by severity, category, and software type",
            ],
        ),
        AgentSkill(
            id="asset-scope-analysis",
            name="Asset Scope Analysis",
            description=(
                "Drills into configuration violations for specific devices or "
                "filtered asset sets. Filterable by hostname, IP, product family, "
                "location, software version, contract, coverage status, and 15+ "
                "other dimensions. Returns per-asset violations, failed rules, "
                "corrective actions, and severity distributions."
            ),
            tags=[
                "asset",
                "device",
                "hostname",
                "ip-address",
                "product-family",
                "product-type",
                "location",
                "software-type",
                "software-version",
                "contract",
                "coverage",
                "lifecycle",
                "criticality",
                "violation",
                "remediation",
                "corrective-action",
            ],
            examples=[
                "Which Cisco product families have the most configuration deviations?",
                "Which assets have the most critical and high severity deviations? What corrective actions are recommended?",
                "Show breakdown of critical and high severity deviations by asset criticality",
                "Show the deviations for asset router-core-01",
                "Compare deviations across the Catalyst and Nexus product families",
            ],
        ),
        AgentSkill(
            id="rule-analysis",
            name="Rule Analysis",
            description=(
                "Explains which best practice rules are being violated, how many "
                "assets are affected, and what remediation to take. Supports "
                "single-rule deep dives by rule ID or name, cross-rule comparisons, "
                "and rule-level summaries with violation counts and severity."
            ),
            tags=[
                "rule",
                "rule-id",
                "rule-category",
                "violation",
                "policy",
                "remediation",
                "corrective-action",
                "impact",
                "risk",
                "cross-rule-comparison",
                "technology",
            ],
            examples=[
                "Which configuration deviations pose the highest risk, and what corrective actions are recommended?",
                "Show me a summary of rule CSCO-0042",
                "For a specific rule, what technology contributes the most violations?",
                "For a specific rule, show only high-severity violations",
                "For all critical rules, show which assets are affected and how to remediate",
            ],
        ),
        AgentSkill(
            id="signature-asset-insights",
            name="Signature Asset Insights",
            description=(
                "Surfaces pre-generated AI insights for Signature-covered assets: "
                "prioritized observations, related rule IDs, impacted asset lists, "
                "and remediation recommendations. Supports listing all insights or "
                "retrieving a specific insight by ID."
            ),
            tags=[
                "insights",
                "signature",
                "ai-generated",
                "recommendations",
                "prioritization",
                "remediation",
                "focus-areas",
            ],
            examples=[
                "Show insights from the latest Signature asset assessment",
                "What are the top Signature asset insights?",
                "Give me details on insight INS-003",
                "What should I focus on first for Signature assets?",
            ],
        ),
    ],
)
