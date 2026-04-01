"""Deep extraction: fetch grandchildren (LLM runs inside route_to_agent and execute_agent)."""
import json, urllib.request, os
from datetime import datetime

API_KEY = os.environ.get("LANGSMITH_API_KEY", "")
BASE_NPRD = "https://langsmith.nprd.usw2.plat.cxp.csco.cloud/api/v1"

def fetch(url):
    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def dur(r):
    s, e = r.get("start_time"), r.get("end_time")
    if not (s and e): return None
    try:
        t0 = datetime.fromisoformat(s.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(e.replace("Z", "+00:00"))
        return round((t1 - t0).total_seconds(), 1)
    except:
        return None

def fetch_descendants(share_token, run, depth=0, max_depth=3):
    """Recursively fetch descendants up to max_depth."""
    indent = "  " * depth
    name = run.get("name", "?")
    rtype = run.get("run_type", "?")
    status = run.get("status", "?")
    tokens = run.get("total_tokens", 0)
    d = dur(run)

    print(f"{indent}[{rtype}] {name} — status={status}, dur={d}s, tokens={tokens}")

    result = {"run": run, "children": []}

    if depth < max_depth:
        child_ids = run.get("direct_child_run_ids") or []
        for cid in child_ids:
            try:
                child = fetch(f"{BASE_NPRD}/public/{share_token}/run/{cid}")
                child_result = fetch_descendants(share_token, child, depth + 1, max_depth)
                result["children"].append(child_result)
            except Exception as e:
                print(f"{indent}  ERROR fetching {cid}: {e}")

    return result

# ============================================================================
# TURN 1
# ============================================================================
print("=" * 80)
print("TURN 1: Correct routing")
print("=" * 80)

t1 = json.load(open("/tmp/turn1_trace.json"))
t1_root = t1.get("root", t1)
t1_token = "4f7bf759-14b7-46e9-8cef-0944f2534875"

# Focus on route_to_agent and execute_agent
t1_children = t1.get("children", [])
t1_route = next((c for c in t1_children if c.get("name") == "route_to_agent"), None)
t1_execute = next((c for c in t1_children if c.get("name") == "execute_agent"), None)

print("\n--- route_to_agent tree ---")
if t1_route:
    t1_route_tree = fetch_descendants(t1_token, t1_route)
else:
    print("NOT FOUND")

print("\n--- execute_agent tree (depth 2 only) ---")
if t1_execute:
    t1_exec_tree = fetch_descendants(t1_token, t1_execute, max_depth=2)
else:
    print("NOT FOUND")

# ============================================================================
# TURN 2
# ============================================================================
print("\n\n" + "=" * 80)
print("TURN 2: Misclassified follow-up")
print("=" * 80)

t2 = json.load(open("/tmp/turn2_trace.json"))
t2_root = t2.get("root", t2)
t2_token = "69b1b31f-574c-4fc5-aecd-92523d5388ec"

t2_children = t2.get("children", [])
t2_route = next((c for c in t2_children if c.get("name") == "route_to_agent"), None)
t2_execute = next((c for c in t2_children if c.get("name") == "execute_agent"), None)

print("\n--- route_to_agent tree ---")
if t2_route:
    t2_route_tree = fetch_descendants(t2_token, t2_route)
else:
    print("NOT FOUND")

print("\n--- execute_agent tree ---")
if t2_execute:
    t2_exec_tree = fetch_descendants(t2_token, t2_execute, max_depth=2)
else:
    print("NOT FOUND")


# ============================================================================
# Now extract the actual LLM data from route_to_agent for both turns
# ============================================================================
def find_llm_runs(tree):
    """Recursively find all llm runs in the tree."""
    results = []
    run = tree.get("run", tree)
    if run.get("run_type") == "llm":
        results.append(run)
    for child in tree.get("children", []):
        results.extend(find_llm_runs(child))
    return results

def extract_llm_detail(llm_run, label):
    print(f"\n{'='*80}")
    print(f" {label}: {llm_run.get('name')}")
    print(f"{'='*80}")

    meta = llm_run.get("extra", {}).get("metadata", {})
    inv = llm_run.get("extra", {}).get("invocation_params", {})
    print(f"Model: {meta.get('ls_model_name', inv.get('model', 'N/A'))}")
    print(f"Provider: {meta.get('ls_provider', 'N/A')}")
    print(f"Temperature: {inv.get('temperature', 'N/A')}")
    print(f"Tokens: prompt={llm_run.get('prompt_tokens')}, completion={llm_run.get('completion_tokens')}, total={llm_run.get('total_tokens')}")

    # Input messages
    msgs = llm_run.get("inputs", {}).get("messages", [[]])
    if msgs and isinstance(msgs[0], list):
        msg_list = msgs[0]
    elif msgs and isinstance(msgs[0], dict):
        msg_list = msgs
    else:
        msg_list = []

    print(f"\nInput messages ({len(msg_list)}):")
    for j, m in enumerate(msg_list):
        msg_id = str(m.get("id", []))
        kwargs = m.get("kwargs", {}) if isinstance(m, dict) and "kwargs" in m else {}
        content = kwargs.get("content", m.get("content", ""))

        if "SystemMessage" in msg_id:
            role = "SYSTEM"
        elif "HumanMessage" in msg_id:
            role = "HUMAN"
        elif "AIMessage" in msg_id:
            role = "AI"
        elif "ToolMessage" in msg_id:
            role = "TOOL"
        else:
            role = m.get("type", "UNKNOWN").upper()

        tool_calls = kwargs.get("tool_calls", m.get("tool_calls", []))

        if role == "SYSTEM":
            print(f"\n  [{j}] {role} ({len(str(content))} chars):")
            print(str(content)[:8000])
            if len(str(content)) > 8000:
                print(f"\n  ... [TRUNCATED at 8000/{len(str(content))} chars] ...")
        elif role == "HUMAN":
            print(f"\n  [{j}] {role} ({len(str(content))} chars):")
            print(str(content)[:8000])
            if len(str(content)) > 8000:
                print(f"\n  ... [TRUNCATED at 8000/{len(str(content))} chars] ...")
        else:
            print(f"\n  [{j}] {role}: {str(content)[:500]}")
            if tool_calls:
                for tc in tool_calls:
                    print(f"       tool_call: {tc.get('name')} -> {json.dumps(tc.get('args', {}))[:300]}")

    # Tool definitions
    tools = inv.get("tools", [])
    if tools:
        print(f"\nTool definitions ({len(tools)}):")
        for t in tools:
            fn = t.get("function", {})
            print(f"  - {fn.get('name')}: {fn.get('description', '')[:150]}")

    # Output
    gens = (llm_run.get("outputs") or {}).get("generations", [[]])
    if gens and gens[0]:
        for g in gens[0]:
            mk = g.get("message", {}).get("kwargs", {})
            out_content = mk.get("content", "")
            out_tool_calls = mk.get("tool_calls", [])
            fr = mk.get("response_metadata", {}).get("finish_reason", "N/A")
            print(f"\nOutput: finish_reason={fr}")
            if out_content:
                print(f"Content ({len(out_content)} chars):")
                print(out_content[:3000])
            if out_tool_calls:
                for tc in out_tool_calls:
                    print(f"Tool call: {tc.get('name')} -> {json.dumps(tc.get('args', {}))[:500]}")

    return llm_run

# Find LLM runs in route_to_agent for both turns
print("\n\n" + "#" * 80)
print("# DETAILED LLM EXTRACTION — ROUTE_TO_AGENT")
print("#" * 80)

if t1_route:
    t1_route_llms = find_llm_runs(t1_route_tree)
    print(f"\nTurn 1 route_to_agent LLM runs: {len(t1_route_llms)}")
    for i, llm in enumerate(t1_route_llms):
        extract_llm_detail(llm, f"TURN 1 / route_to_agent / LLM[{i}]")

if t2_route:
    t2_route_llms = find_llm_runs(t2_route_tree)
    print(f"\nTurn 2 route_to_agent LLM runs: {len(t2_route_llms)}")
    for i, llm in enumerate(t2_route_llms):
        extract_llm_detail(llm, f"TURN 2 / route_to_agent / LLM[{i}]")

# Also extract execute_agent LLM details for context
print("\n\n" + "#" * 80)
print("# DETAILED LLM EXTRACTION — EXECUTE_AGENT")
print("#" * 80)

if t1_execute:
    t1_exec_llms = find_llm_runs(t1_exec_tree)
    print(f"\nTurn 1 execute_agent LLM runs: {len(t1_exec_llms)}")
    for i, llm in enumerate(t1_exec_llms):
        extract_llm_detail(llm, f"TURN 1 / execute_agent / LLM[{i}]")

if t2_execute:
    t2_exec_llms = find_llm_runs(t2_exec_tree)
    print(f"\nTurn 2 execute_agent LLM runs: {len(t2_exec_llms)}")
    for i, llm in enumerate(t2_exec_llms):
        extract_llm_detail(llm, f"TURN 2 / execute_agent / LLM[{i}]")
