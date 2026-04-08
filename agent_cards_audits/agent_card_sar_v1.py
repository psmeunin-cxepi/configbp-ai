import os
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, AgentInterface

# --- Static reasoning examples ---
STATIC_REASONING_QUESTIONS = [
    "Validate the SLIC result for PSIRT-2024-0001 on this device.",
    "Does the SLIC analysis match the raw PSIRT details?",
    "Is the hardening compliance result correct for this device telemetry?",
    "Check if the vulnerability determination is accurate given the PSIRT and telemetry.",
]

host = os.getenv("SA_AI_REASONING_A2A_HOST", "0.0.0.0")
port = int(os.getenv("SA_AI_REASONING_A2A_PORT", "8012"))
base_url = os.getenv("SA_AI_REASONING_A2A_BASE", f"http://{host}:{port}")

sa_ai_reasoning = AgentSkill(
    id="sa-ai-reasoning",
    name="SLIC Result Validation",
    description=(
        "Validates SLIC results against device telemetry and raw PSIRT content. "
        "Explains whether the vulnerability or hardening assessment is correct and why."
    ),
    tags=[
        "security-assessment",
        "psirt",
        "slic",
        "slic-verification",
        "vulnerability",
        "hardening-check",
        "assessment-validation",
    ],
    examples=STATIC_REASONING_QUESTIONS,
)

card = AgentCard(
    name="Security Assessment – SLIC Reasoning",
    description=(
        "Validates SLIC vulnerability and hardening assessment results against raw "
        "PSIRT advisories and device telemetry. Route here for SLIC result "
        "verification and reasoning; do not route here for general PSIRT lookups, "
        "configuration compliance, or risk scoring."
    ),
    version="1.0.0",
    supported_interfaces=[
        AgentInterface(
            url=base_url,
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        ),
    ],
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[sa_ai_reasoning],
)
