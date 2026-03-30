#!/usr/bin/env python3
"""Analyze a LangSmith public trace in detail."""
import json, urllib.request, os
from datetime import datetime

BASE = "https://langsmith.prod.usw2.plat.cxp.csco.cloud/api/v1"
TOKEN = "ef1da42a-c1ae-412e-a4d0-9e2165c3e0b8"
KEY = os.environ.get("LANGSMITH_API_KEY", "")

def fetch(url):
    headers = {"x-api-key": KEY} if KEY else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

root = fetch(f"{BASE}/public/{TOKEN}/run")

# Extract message sequence
msgs = root["inputs"]["messages"][0]
print("=" * 60)
print("FULL CONVERSATION FLOW")
print("=" * 60)

for i, msg in enumerate(msgs):
    kwargs = msg.get("kwargs", {})
    msg_id = str(msg.get("id", []))

    if "SystemMessage" in msg_id:
        content = kwargs.get("content", "")
        print(f"\n[{i}] SYSTEM: ({len(content)} chars)")
    elif "HumanMessage" in msg_id:
        print(f"\n[{i}] HUMAN: {kwargs.get('content', '')[:200]}")
    elif "AIMessage" in msg_id:
        content = kwargs.get("content", "")
        tcs = kwargs.get("tool_calls", [])
        rm = kwargs.get("response_metadata", {})
        tu = rm.get("token_usage", {})
        model = rm.get("model_name", "?")
        finish = rm.get("finish_reason", "?")
        print(f"\n[{i}] AI (model={model}, finish={finish}, tokens={tu.get('total_tokens', '?')}):")
        if content:
            print(f"    Content: {content[:500]}")
        for tc in tcs:
            print(f"    Tool call: {tc['name']}({json.dumps(tc['args'])})")
    elif "ToolMessage" in msg_id:
        status = kwargs.get("status", "?")
        name = kwargs.get("name", "?")
        content = kwargs.get("content", "")[:300]
        print(f"\n[{i}] TOOL ({name}, status={status}): {content}")

# Final LLM output
print("\n" + "=" * 60)
print("FINAL LLM OUTPUT (this step)")
print("=" * 60)
gens = root.get("outputs", {}).get("generations", [[]])
for g in gens[0]:
    mk = g.get("message", {}).get("kwargs", {})
    content = mk.get("content", "")
    if content:
        print(f"Content: {content[:3000]}")
    for tc in mk.get("tool_calls", []):
        print(f"Tool call: {tc['name']}({json.dumps(tc['args'])})")

# Timing
start = root.get("start_time", "")
end = root.get("end_time", "")
if start and end:
    s = datetime.fromisoformat(start.replace("Z", "+00:00"))
    e = datetime.fromisoformat(end.replace("Z", "+00:00"))
    print(f"\nDuration: {(e - s).total_seconds():.2f}s")
    print(f"Start: {start}")
    print(f"End: {end}")

print(f"\nParent run ID: {root.get('parent_run_id', 'None')}")
print(f"Trace ID: {root.get('trace_id')}")
print(f"Tags: {root.get('tags')}")

# Available tools
extra = root.get("extra", {})
invocation = extra.get("invocation_params", {})
tools = invocation.get("tools", [])
print(f"\n{'=' * 60}")
print(f"AVAILABLE TOOLS ({len(tools)})")
print(f"{'=' * 60}")
for t in tools:
    fn = t.get("function", {})
    print(f"  - {fn.get('name', '?')}: {fn.get('description', '')[:120]}")

# Token analysis across all AI messages
print(f"\n{'=' * 60}")
print("CUMULATIVE TOKEN USAGE (all AI steps in context)")
print(f"{'=' * 60}")
total_prompt = 0
total_completion = 0
total_cached = 0
total_reasoning = 0
step = 0
for msg in msgs:
    msg_id = str(msg.get("id", []))
    if "AIMessage" in msg_id:
        step += 1
        tu = msg["kwargs"].get("response_metadata", {}).get("token_usage", {})
        pt = tu.get("prompt_tokens", 0)
        ct = tu.get("completion_tokens", 0)
        cached = tu.get("prompt_tokens_details", {}).get("cached_tokens", 0)
        reasoning = tu.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        print(f"  Step {step}: {pt} prompt ({cached} cached) + {ct} completion ({reasoning} reasoning) = {pt + ct} total")
        total_prompt += pt
        total_completion += ct
        total_cached += cached
        total_reasoning += reasoning

# Add final step from this run
final_tu = root.get("outputs", {}).get("llm_output", {}).get("token_usage", {})
if final_tu:
    pt = final_tu.get("prompt_tokens", 0)
    ct = final_tu.get("completion_tokens", 0)
    cached = final_tu.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    reasoning = final_tu.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
    step += 1
    print(f"  Step {step} (current): {pt} prompt ({cached} cached) + {ct} completion ({reasoning} reasoning) = {pt + ct} total")
    total_prompt += pt
    total_completion += ct
    total_cached += cached
    total_reasoning += reasoning

print(f"\n  TOTAL: {total_prompt} prompt ({total_cached} cached) + {total_completion} completion ({total_reasoning} reasoning) = {total_prompt + total_completion} tokens")
