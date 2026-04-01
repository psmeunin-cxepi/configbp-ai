"""Extract the full HUMAN message from Turn 2's route_to_agent LLM call, plus Turn 1 routing details."""
import json

def load(path):
    with open(path) as f:
        return json.load(f)

# ============================================================================
# TURN 1: How was routing done without an LLM call?
# ============================================================================
print("=" * 80)
print("TURN 1: route_to_agent — NO LLM CALL, how was routing done?")
print("=" * 80)

t1 = load("/tmp/turn1_trace.json")
t1_children = t1.get("children", [])

# Look at all children's inputs/outputs
for c in t1_children:
    name = c.get("name", "?")
    inp = c.get("inputs", {})
    out = c.get("outputs", {})
    print(f"\n--- {name} ---")
    print(f"  Input keys: {list(inp.keys())}")
    if inp:
        for k, v in inp.items():
            vs = json.dumps(v, default=str) if not isinstance(v, str) else v
            print(f"  Input[{k}]: {vs[:500]}")
    print(f"  Output keys: {list(out.keys())}")
    if out:
        for k, v in out.items():
            vs = json.dumps(v, default=str) if not isinstance(v, str) else v
            print(f"  Output[{k}]: {vs[:500]}")

# ============================================================================
# TURN 2: Full HUMAN message from route_to_agent LLM
# ============================================================================
print("\n\n" + "=" * 80)
print("TURN 2: route_to_agent — Full HUMAN message")
print("=" * 80)

t2 = load("/tmp/turn2_trace.json")
t2_children = t2.get("children", [])

# Same: look at all children's inputs/outputs
print("\n--- All children I/O summary ---")
for c in t2_children:
    name = c.get("name", "?")
    inp = c.get("inputs", {})
    out = c.get("outputs", {})
    print(f"\n--- {name} ---")
    print(f"  Input keys: {list(inp.keys())}")
    if inp:
        for k, v in inp.items():
            vs = json.dumps(v, default=str) if not isinstance(v, str) else v
            print(f"  Input[{k}]: {vs[:500]}")
    print(f"  Output keys: {list(out.keys())}")
    if out:
        for k, v in out.items():
            vs = json.dumps(v, default=str) if not isinstance(v, str) else v
            print(f"  Output[{k}]: {vs[:500]}")

# ============================================================================
# TURN 2: The actual full HUMAN message passed to Mistral in route_to_agent
# ============================================================================
print("\n\n" + "=" * 80)
print("TURN 2: The FULL human message content from ChatMistralAI")
print("=" * 80)

# We need to re-fetch the LLM child. Let me find it in the trace data.
# The LLM is a grandchild of route_to_agent
t2_route = next((c for c in t2_children if c.get("name") == "route_to_agent"), None)
if t2_route:
    # We know from the tree: route_to_agent > RunnableSequence > ChatMistralAI
    # The ChatMistralAI child_ids are inside route_to_agent's children
    route_child_ids = t2_route.get("direct_child_run_ids", [])
    print(f"route_to_agent direct_child_run_ids: {route_child_ids}")

    # We already fetched this in the deep extract. Let me look at outputs of route_to_agent
    print(f"\nroute_to_agent outputs: {json.dumps(t2_route.get('outputs', {}), default=str)[:1000]}")
    print(f"\nroute_to_agent inputs: {json.dumps(t2_route.get('inputs', {}), default=str)[:1000]}")

# Write the full human message to a file for inspection
# The data is available in the deep extract output from the LLM child
# Let me reconstruct it from the trace file
# The LLM run is inside route_to_agent > RunnableSequence > ChatMistralAI
# I need to access it via the cached grandchild data

# Actually, let me extract the agent cards and conversation context from the human message
# by looking at what fetch_recent_context_db returned
t2_fetch_ctx = next((c for c in t2_children if c.get("name") == "fetch_recent_context_db"), None)
if t2_fetch_ctx:
    print("\n\n--- fetch_recent_context_db ---")
    print(f"  Inputs: {json.dumps(t2_fetch_ctx.get('inputs', {}), default=str)[:1000]}")
    print(f"  Outputs: {json.dumps(t2_fetch_ctx.get('outputs', {}), default=str)[:2000]}")

# Also check execute_agent outputs for Turn 2
t2_execute = next((c for c in t2_children if c.get("name") == "execute_agent"), None)
if t2_execute:
    print("\n\n--- execute_agent (Turn 2) ---")
    print(f"  Inputs: {json.dumps(t2_execute.get('inputs', {}), default=str)[:1000]}")
    out = t2_execute.get("outputs", {})
    print(f"  Outputs: {json.dumps(out, default=str)[:3000]}")
