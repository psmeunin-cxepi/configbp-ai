## Category 1: Qualitative "Hype" (Subjective Adjectives)
These words add zero functional information and confuse the model’s weightings.

The List: helpful, smart, intelligent, powerful, advanced, best, expert, reliable, seamless, innovative, efficient, fast, robust, top-tier.

Audit Logic: If an agent is "efficient," how does the router distinguish it from an agent that is "fast"?

Replacement: Use quantitative constraints (e.g., "Latency < 200ms" or "Supports 10k+ rows").

## Category 2: Indefinite Quantifiers (Scope Hiders)
These words are used by developers to avoid defining the actual boundaries of the agent.

The List: various, many, several, multiple, diverse, all kinds of, etc., and more, etcetera.

Audit Logic: These terms force the LLM to guess the scope.

Replacement: List the specific 3–5 primary objects handled (e.g., "Processes .pdf and .docx" instead of "various file types").

## Category 3: Agentic Fillers (Identity Fluff)
Phrases that state the obvious about being an AI or a software component.

The List: I am an agent that..., Designed to help with..., Works to provide..., Can be used for..., Specializes in..., This skill allows the user to....

Audit Logic: Every entry in an A2A registry is an agent/skill. These phrases waste "Attention Tokens."

Replacement: Start directly with a functional verb (e.g., "Calculates..." or "Authenticates...").

## Category 4: High-Entropy Nouns (The "Noise" Makers)
These terms are so common across all business domains that they create "Semantic Clusters" where unrelated agents collide.

The List: data, information, details, task, activity, solution, system, tool, process, logic.

Audit Logic: If 50 agents use the word "data," the word "data" becomes a stop-word with zero routing value.

Replacement: Be specific to the domain (e.g., telemetry, ledger-entry, user-profile, auth-token).

## Category 5: Low-Resolution Artifacts (Vague Results)
Words that describe a result without defining its content or shape.

The List: summary, assessment, risk, report, analysis, output, result.

Audit Logic: These terms trigger too many broad intents.

Replacement: Qualify the term (e.g., VAT-compliance-summary, credit-default-risk, inventory-delta-report).