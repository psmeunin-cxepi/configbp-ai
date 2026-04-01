"""Extract the FULL human message from Turn 2's ChatMistralAI LLM call."""
import json, urllib.request, os

API_KEY = os.environ.get("LANGSMITH_API_KEY", "")
BASE = "https://langsmith.nprd.usw2.plat.cxp.csco.cloud/api/v1"
T2_TOKEN = "69b1b31f-574c-4fc5-aecd-92523d5388ec"

def fetch(url):
    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

# The RunnableSequence child of route_to_agent
# From deep extract: route_to_agent > RunnableSequence > ChatMistralAI
# RunnableSequence child ID from route_to_agent
t2 = json.load(open("/tmp/turn2_trace.json"))
t2_children = t2.get("children", [])
t2_route = next((c for c in t2_children if c.get("name") == "route_to_agent"), None)

# Fetch grandchildren of route_to_agent
for cid in t2_route.get("direct_child_run_ids", []):
    gc = fetch(f"{BASE}/public/{T2_TOKEN}/run/{cid}")
    print(f"Grandchild: name={gc.get('name')}, run_type={gc.get('run_type')}")

    if gc.get("name") == "RunnableSequence":
        # Get LLM run inside RunnableSequence
        for gcid in gc.get("direct_child_run_ids", []):
            ggc = fetch(f"{BASE}/public/{T2_TOKEN}/run/{gcid}")
            if ggc.get("run_type") == "llm":
                print(f"\nFound LLM: name={ggc.get('name')}")

                msgs = ggc.get("inputs", {}).get("messages", [[]])
                if msgs and isinstance(msgs[0], list):
                    msg_list = msgs[0]
                else:
                    msg_list = msgs

                for j, m in enumerate(msg_list):
                    msg_id = str(m.get("id", []))
                    kwargs = m.get("kwargs", {}) if "kwargs" in m else {}
                    content = kwargs.get("content", m.get("content", ""))

                    if "SystemMessage" in msg_id:
                        role = "SYSTEM"
                    elif "HumanMessage" in msg_id:
                        role = "HUMAN"
                    else:
                        role = "OTHER"

                    print(f"\n{'='*80}")
                    print(f"Message [{j}] - {role} ({len(str(content))} chars)")
                    print(f"{'='*80}")
                    # Print the FULL content
                    print(content)

                # Also print the tool definition used
                inv = ggc.get("extra", {}).get("invocation_params", {})
                tools = inv.get("tools", [])
                if tools:
                    print(f"\n{'='*80}")
                    print(f"TOOL DEFINITIONS ({len(tools)})")
                    print(f"{'='*80}")
                    print(json.dumps(tools, indent=2))

                # Print the output
                gens = (ggc.get("outputs") or {}).get("generations", [[]])
                if gens and gens[0]:
                    print(f"\n{'='*80}")
                    print("LLM OUTPUT")
                    print(f"{'='*80}")
                    for g in gens[0]:
                        mk = g.get("message", {}).get("kwargs", {})
                        print(f"finish_reason: {mk.get('response_metadata', {}).get('finish_reason')}")
                        if mk.get("content"):
                            print(f"Content: {mk['content']}")
                        for tc in mk.get("tool_calls", []):
                            print(f"Tool call: {tc.get('name')} -> {json.dumps(tc.get('args', {}))}")
