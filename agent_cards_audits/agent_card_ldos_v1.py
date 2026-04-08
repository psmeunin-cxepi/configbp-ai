import os
from a2a.types import AgentCard, AgentCapabilities, AgentInterface
from skills import ask_cvi_ldos_ai_internal, ask_cvi_ldos_ai_external

host = os.getenv("LDOS_A2A_HOST", "0.0.0.0")
port = int(os.getenv("LDOS_A2A_PORT", "8002"))
base_url = os.getenv("LDOS_A2A_BASE", f"http://{host}:{port}")

skills = [
    ask_cvi_ldos_ai_internal,
    ask_cvi_ldos_ai_external,
]

card = AgentCard(
    name="Assets (General)",
    description=(
        "Answers questions about a customer's Cisco network asset inventory and "
        "lifecycle data — device counts, LDOS/end-of-life milestones, coverage and "
        "contract status, telemetry/connectivity, tags, locations, and sub-components. "
        "Route here for asset inventory and lifecycle questions; do not route here "
        "for criticality, PIN-based prioritization, or risk ranking (use Asset "
        "Criticality agent instead)."
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
