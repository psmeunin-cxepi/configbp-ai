#!/usr/bin/env python3
"""Fetch partial-failure trace and extract full analysis."""
import json, subprocess, os, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ[k.strip()] = v.strip().strip('"')

url = "https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/2ba9d014-85d7-4954-9e8e-4b3c2ad49c76/r"
script = ".agents/skills/langsmith-trace/scripts/fetch_trace.py"

result = subprocess.run(
    [sys.executable, script, url, "--mode", "raw"],
    capture_output=True, text=True, timeout=120,
)
if result.returncode != 0:
    print("ERROR:", result.stderr[:500])
    sys.exit(1)

with open("/tmp/trace4.json", "w") as f:
    f.write(result.stdout)

data = json.loads(result.stdout)
root = data.get("root", data)
children = data.get("children", [])

from datetime import datetime
def dur(s, e):
    if not (s and e):
        return None
    try:
        return round((datetime.fromisoformat(e.replace("Z","+00:00")) - datetime.fromisoformat(s.replace("Z","+00:00"))).total_seconds(), 1)
    except:
        return None

print(f"Size: {len(result.stdout)} bytes")
print(f"Run type: {root.get('run_type')}")
print(f"Name: {root.get('name')}")
print(f"Status: {root.get('status')}")
print(f"Error: {root.get('error')}")
d = dur(root.get("start_time"), root.get("end_time"))
print(f"Duration: {d}s")
print(f"Tokens: prompt={root.get('prompt_tokens')}, completion={root.get('completion_tokens')}, total={root.get('total_tokens')}")
ptd = root.get("prompt_token_details") or {}
ctd = root.get("completion_token_details") or {}
print(f"Cache read: {ptd.get('cache_read', 0)}, Reasoning: {ctd.get('reasoning', 0)}")
meta = root.get("extra", {}).get("metadata", {})
print(f"Revision: {meta.get('revision_id', 'N/A')}")

print(f"\nDirect children ({len(children)}):")
for c in children:
    if c.get("fetch_error"):
        print(f"  FETCH ERROR: {c['fetch_error']}")
        continue
    cd = dur(c.get("start_time"), c.get("end_time"))
    print(f"  - {c.get('name')} (run_type={c.get('run_type')}, status={c.get('status')}, dur={cd}s, tokens={c.get('total_tokens', 0)})")

# Message flow
msgs = root.get("outputs", {}).get("messages", [])
print(f"\nMessage flow ({len(msgs)} messages):")
for i, msg in enumerate(msgs):
    mtype = msg.get("type", "?")
    if mtype == "human":
        print(f"  [{i}] HUMAN: {msg.get('content', '')[:120]}")
    elif mtype == "ai":
        tcs = msg.get("tool_calls", [])
        content = msg.get("content", "")
        rm = msg.get("response_metadata", {})
        finish = rm.get("finish_reason", "?")
        model = rm.get("model_name", "?")
        tu = rm.get("token_usage", {})
        cached = (tu.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
        reasoning = (tu.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
        if tcs:
            print(f"  [{i}] AI (finish={finish}, model={model}): {len(tcs)} tool calls")
            for tc in tcs:
                args_str = json.dumps(tc.get("args", {}))
                print(f"        -> {tc.get('name')}({args_str})")
            if tu:
                print(f"        tokens: p={tu.get('prompt_tokens')}, c={tu.get('completion_tokens')}, cached={cached}, reasoning={reasoning}")
        else:
            print(f"  [{i}] AI RESPONSE (finish={finish}):")
            if tu:
                print(f"        tokens: p={tu.get('prompt_tokens','?')}, c={tu.get('completion_tokens','?')}, cached={cached}, reasoning={reasoning}")
            print("        ---START---")
            print(content)
            print("        ---END---")
    elif mtype == "tool":
        status = msg.get("status", "")
        name = msg.get("name", "?")
        content = msg.get("content", "")
        tcid = msg.get("tool_call_id", "")
        if status == "error":
            print(f"  [{i}] TOOL ERROR ({name}, call_id={tcid}): {content[:300]}")
        else:
            print(f"  [{i}] TOOL OK ({name}, status={status}, call_id={tcid}): {content[:400]}...")

# Extra outputs
eo = root.get("outputs", {}).get("effective_intent")
ft = root.get("outputs", {}).get("flow_type")
print(f"\nEffective intent: {eo}, Flow type: {ft}")
