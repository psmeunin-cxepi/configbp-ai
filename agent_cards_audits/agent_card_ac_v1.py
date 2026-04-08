import os
from a2a.types import AgentCard, AgentCapabilities, AgentInterface
from skills import ask_asset_criticality

host = os.getenv("LDOS_A2A_HOST", "0.0.0.0")
port = int(os.getenv("LDOS_CRITICALITY_A2A_PORT", "8003"))
base_url = os.getenv("LDOS_CRITICALITY_A2A_BASE", f"http://{host}:{port}")

skills = [
    ask_asset_criticality,
]

card = AgentCard(
    name="Asset Criticality",
    description=(
        "Answers questions about asset risk, criticality, and prioritization for "
        "Cisco network devices — Place in Network (PIN) role/importance, security "
        "advisory and field notice severity correlated with device importance, and "
        "risk-based refresh/coverage recommendations. Route here for criticality "
        "and prioritization questions; do not route here for general asset inventory "
        "or lifecycle queries without a risk/importance angle."
    ),
    version="1.0.0",
    supported_interfaces=[
        AgentInterface(
            url=base_url,
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        ),
    ],
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=skills,
)
