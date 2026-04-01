"""Extract key data from Turn 1 and Turn 2 traces for multi-turn analysis."""
import json, sys, textwrap

def load(path):
    with open(path) as f:
        return json.load(f)

def dur(r):
    from datetime import datetime
    s, e = r.get("start_time"), r.get("end_time")
    if not (s and e):
        return None
    try:
        t0 = datetime.fromisoformat(s.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(e.replace("Z", "+00:00"))
        return round((t1 - t0).total_seconds(), 1)
    except:
        return None

def extract_trace(data, label):
    root = data.get("root", data)
    children = data.get("children", [])

    print(f"\n{'='*80}")
    print(f" {label}")
    print(f"{'='*80}")

    # Root metadata
    print(f"\nRoot: name={root.get('name')}, run_type={root.get('run_type')}, status={root.get('status')}")
    print(f"Duration: {dur(root)}s, Tokens: {root.get('total_tokens')}")
    print(f"Error: {root.get('error')}")
    extra = root.get("extra", {}).get("metadata", {})
    print(f"Revision: {extra.get('revision_id', 'N/A')}")

    # Children summary
    print(f"\nDirect children ({len(children)}):")
    for i, c in enumerate(children):
        print(f"  [{i}] name={c.get('name')}, run_type={c.get('run_type')}, status={c.get('status')}, dur={dur(c)}s, tokens={c.get('total_tokens')}")

    # Find LLM children (where system prompts and tool defs live)
    llm_children = [c for c in children if c.get("run_type") == "llm"]
    print(f"\nLLM children: {len(llm_children)}")

    for i, llm in enumerate(llm_children):
        print(f"\n--- LLM Child [{i}]: name={llm.get('name')} ---")
        meta = llm.get("extra", {}).get("metadata", {})
        inv = llm.get("extra", {}).get("invocation_params", {})
        print(f"  Model: {meta.get('ls_model_name', inv.get('model', 'N/A'))}")
        print(f"  Provider: {meta.get('ls_provider', 'N/A')}")
        print(f"  Temperature: {inv.get('temperature', 'N/A')}")
        print(f"  Tokens: prompt={llm.get('prompt_tokens')}, completion={llm.get('completion_tokens')}, total={llm.get('total_tokens')}")

        # Extract messages from this LLM child
        msgs = llm.get("inputs", {}).get("messages", [[]])
        if msgs and isinstance(msgs[0], list):
            msg_list = msgs[0]
        elif msgs and isinstance(msgs[0], dict):
            msg_list = msgs
        else:
            msg_list = []

        print(f"  Input messages: {len(msg_list)}")
        for j, m in enumerate(msg_list):
            msg_id = str(m.get("id", []))
            kwargs = m.get("kwargs", {}) if isinstance(m, dict) and "kwargs" in m else {}

            # Determine role
            if "SystemMessage" in msg_id:
                role = "SYSTEM"
            elif "HumanMessage" in msg_id:
                role = "HUMAN"
            elif "AIMessage" in msg_id:
                role = "AI"
            elif "ToolMessage" in msg_id:
                role = "TOOL"
            elif m.get("type"):
                role = m["type"].upper()
            else:
                role = "UNKNOWN"

            content = kwargs.get("content", m.get("content", ""))
            content_preview = str(content)[:300] if content else "(empty)"

            tool_calls = kwargs.get("tool_calls", m.get("tool_calls", []))

            print(f"    [{j}] {role}: {content_preview}")
            if tool_calls:
                for tc in tool_calls:
                    print(f"         tool_call: {tc.get('name')} -> args_keys={list(tc.get('args', {}).keys())}")

        # Extract tool definitions
        tools = inv.get("tools", [])
        if tools:
            print(f"  Tool definitions ({len(tools)}):")
            for t in tools:
                fn = t.get("function", {})
                print(f"    - {fn.get('name')}: {fn.get('description', '')[:100]}")

        # Extract output
        gens = (llm.get("outputs") or {}).get("generations", [[]])
        if gens and gens[0]:
            for g in gens[0]:
                mk = g.get("message", {}).get("kwargs", {})
                out_content = mk.get("content", "")[:500]
                out_tool_calls = mk.get("tool_calls", [])
                fr = mk.get("response_metadata", {}).get("finish_reason", "N/A")
                print(f"  Output: finish_reason={fr}, content_len={len(mk.get('content', ''))}")
                if out_content:
                    print(f"  Output preview: {out_content}")
                if out_tool_calls:
                    for tc in out_tool_calls:
                        print(f"  Output tool_call: {tc.get('name')} -> {json.dumps(tc.get('args', {}))[:200]}")

    # Root-level message flow (flat format)
    root_msgs = root.get("outputs", {}).get("messages", [])
    if root_msgs:
        print(f"\n--- Root output messages ({len(root_msgs)}) ---")
        for i, m in enumerate(root_msgs):
            role = m.get("type", "?").upper()
            content = str(m.get("content", ""))[:300]
            tc = m.get("tool_calls", [])
            name = m.get("name", "")
            status = m.get("status", "")
            extra_info = f" name={name}" if name else ""
            extra_info += f" status={status}" if status else ""
            print(f"  [{i}] {role}{extra_info}: {content}")
            if tc:
                for t in tc:
                    print(f"       tool_call: {t.get('name')} -> {json.dumps(t.get('args', {}))[:200]}")

    # Root-level input
    root_input = root.get("inputs", {})
    if root_input:
        print(f"\n--- Root input ---")
        # Try common structures
        inp_msg = root_input.get("messages", root_input.get("input", ""))
        if isinstance(inp_msg, list) and inp_msg:
            for m in inp_msg:
                if isinstance(m, dict):
                    print(f"  {m.get('type', m.get('role', '?'))}: {str(m.get('content', ''))[:500]}")
                elif isinstance(m, list):
                    for sub in m:
                        if isinstance(sub, dict):
                            print(f"  {sub.get('type', sub.get('role', '?'))}: {str(sub.get('content', ''))[:500]}")
        elif isinstance(inp_msg, str):
            print(f"  {inp_msg[:500]}")
        else:
            print(f"  keys: {list(root_input.keys())}")

    return root, children, llm_children


# --- Load and extract both traces ---
t1 = load("/tmp/turn1_trace.json")
t2 = load("/tmp/turn2_trace.json")

print("=" * 80)
print(" TURN 1: Correct routing (CBP summary)")
print("=" * 80)
r1, c1, llm1 = extract_trace(t1, "TURN 1 — Correct Classification")

print("\n" * 3)

print("=" * 80)
print(" TURN 2: Misclassified follow-up (C9410R recommendation)")
print("=" * 80)
r2, c2, llm2 = extract_trace(t2, "TURN 2 — Misclassified Follow-up")

# --- Deep dive: system prompts ---
print("\n\n")
print("=" * 80)
print(" SYSTEM PROMPTS COMPARISON")
print("=" * 80)

for turn_label, llms in [("TURN 1", llm1), ("TURN 2", llm2)]:
    for i, llm in enumerate(llms):
        msgs = llm.get("inputs", {}).get("messages", [[]])
        if msgs and isinstance(msgs[0], list):
            msg_list = msgs[0]
        elif msgs and isinstance(msgs[0], dict):
            msg_list = msgs
        else:
            msg_list = []

        for m in msg_list:
            msg_id = str(m.get("id", []))
            if "SystemMessage" in msg_id:
                content = m.get("kwargs", {}).get("content", "")
                print(f"\n--- {turn_label} / LLM[{i}] ({llm.get('name')}) System Prompt ---")
                print(f"Length: {len(content)} chars")
                print(content[:5000])
                if len(content) > 5000:
                    print(f"\n... [TRUNCATED, total {len(content)} chars] ...")
                    print(content[-2000:])
                break

# --- Deep dive: Human messages in Turn 2 to see conversation context ---
print("\n\n")
print("=" * 80)
print(" TURN 2 — HUMAN MESSAGES (looking for conversation context)")
print("=" * 80)

for i, llm in enumerate(llm2):
    msgs = llm.get("inputs", {}).get("messages", [[]])
    if msgs and isinstance(msgs[0], list):
        msg_list = msgs[0]
    elif msgs and isinstance(msgs[0], dict):
        msg_list = msgs
    else:
        msg_list = []

    for j, m in enumerate(msg_list):
        msg_id = str(m.get("id", []))
        kwargs = m.get("kwargs", {}) if isinstance(m, dict) and "kwargs" in m else {}
        content = kwargs.get("content", m.get("content", ""))

        if "HumanMessage" in msg_id or m.get("type") == "human":
            print(f"\n--- LLM[{i}] ({llm.get('name')}) / Message[{j}] HUMAN ---")
            print(f"Length: {len(str(content))} chars")
            print(str(content)[:5000])
            if len(str(content)) > 5000:
                print(f"\n... [TRUNCATED, total {len(str(content))} chars] ...")
