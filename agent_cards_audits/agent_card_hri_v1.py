import os
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, AgentInterface

# Get A2A server URL from environment (fallback to localhost for development)
A2A_BASE_URL = os.getenv("A2A_BASE_URL", "http://localhost:9000")

# Define agent card using the proper A2A types
AGENT_CARD = AgentCard(
    name="Assessments – Health Risk Insights",
    version="1.0.0",
    description=(
        "Analyzes Cisco Health Risk Scores for network assets — risk breakdowns, "
        "category distributions, and remediation prioritization. Route here for "
        "health-risk and asset-risk questions; do not route here for configuration "
        "compliance, feature adoption, or lifecycle planning."
    ),
    supported_interfaces=[
        AgentInterface(
            url=A2A_BASE_URL,
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        ),
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True, push_notifications=False),
    skills=[
        AgentSkill(
            id="health-risk-analysis-query",
            name="Health Risk Analysis",
            description=(
                "Analyzes aggregate health risk data — risk score breakdowns by "
                "category, critical/high/medium/low asset distributions, and "
                "remediation prioritization across the customer's asset base."
            ),
            tags=[
                "health-risk",
                "risk-score",
                "risk-analysis",
                "risk-breakdown",
                "risk-categorization",
                "remediation-priority",
                "asset-risk-distribution",
            ],
            examples=[
                "Are any of my Yellow assets borderline Orange?",
                "I have many Critical assets. Which one is the absolute highest priority for my team?",
                "Are there any Critical/Red risk on my low-importance lab devices that I can safely ignore for now?",
                "How much of my Critical risk is due to actual security threats versus config assessment threats?",
            ],
        ),
        AgentSkill(
            id="health-risk-individual-rating-query",
            name="Individual Asset Health Risk Rating",
            description=(
                "Provides a detailed health risk analysis for a single asset or device "
                "identified by hostname or asset ID — risk score, contributing factors, "
                "assessment findings, and remediation guidance."
            ),
            tags=[
                "individual-asset",
                "risk-rating",
                "risk-detail",
                "risk-factors",
                "device",
                "hostname",
                "single-asset-detail",
            ],
            examples=[
                "Why is my asset XXX marked as Red?",
                "My asset XXX has hundreds of findings but is only Orange. Why isn't it Red?",
                "Show me the risk factors for router ABC.",
            ],
        ),
    ],
)
