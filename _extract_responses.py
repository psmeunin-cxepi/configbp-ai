"""Extract Turn 2 final response and Turn 1 CBP response for completeness."""
import json

t2 = json.load(open("/tmp/turn2_trace.json"))
t2_children = t2.get("children", [])
t2_execute = next((c for c in t2_children if c.get("name") == "execute_agent"), None)

print("=" * 80)
print("TURN 2: execute_agent final_response")
print("=" * 80)
if t2_execute:
    fr = t2_execute.get("outputs", {}).get("final_response", {})
    if isinstance(fr, str):
        fr = json.loads(fr)
    print(json.dumps(fr, indent=2, default=str)[:5000])

# Turn 1 CBP response
t1 = json.load(open("/tmp/turn1_trace.json"))
t1_children = t1.get("children", [])
t1_execute = next((c for c in t1_children if c.get("name") == "execute_agent"), None)

print("\n\n" + "=" * 80)
print("TURN 1: execute_agent final_response (CBP response)")
print("=" * 80)
if t1_execute:
    fr = t1_execute.get("outputs", {}).get("final_response", {})
    if isinstance(fr, str):
        fr = json.loads(fr)
    print(json.dumps(fr, indent=2, default=str)[:8000])

# Check the recent_context_structured to see what conversation history was passed to Turn 2
print("\n\n" + "=" * 80)
print("TURN 2: recent_context_structured (conversation history)")
print("=" * 80)
t2_route = next((c for c in t2_children if c.get("name") == "route_to_agent"), None)
if t2_route:
    rcs = t2_route.get("inputs", {}).get("recent_context_structured", {})
    if isinstance(rcs, str):
        rcs = json.loads(rcs)
    print(json.dumps(rcs, indent=2, default=str)[:8000])
