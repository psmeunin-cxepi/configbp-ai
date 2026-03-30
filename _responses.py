#!/usr/bin/env python3
"""Extract full final responses and per-LLM-call token details."""
import json

def load(path):
    with open(path) as f:
        return json.load(f)

for label, path in [("TRACE 1", "/tmp/trace1.json"), ("TRACE 2", "/tmp/trace2.json"), ("TRACE 3", "/tmp/trace3.json")]:
    data = load(path)
    root = data["root"]
    msgs = root.get("outputs", {}).get("messages", [])
    
    print(f"\n{'='*80}")
    print(f" {label} — Full AI responses + token per step")
    print(f"{'='*80}")

    step = 0
    for i, msg in enumerate(msgs):
        mtype = msg.get("type", "?")
        if mtype == "ai":
            step += 1
            tcs = msg.get("tool_calls", [])
            content = msg.get("content", "")
            rm = msg.get("response_metadata", {})
            tu = rm.get("token_usage", {})
            finish = rm.get("finish_reason", "N/A")
            
            cached = (tu.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
            reasoning = (tu.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
            
            print(f"\n  LLM Call {step}: finish_reason={finish}")
            print(f"    prompt={tu.get('prompt_tokens', '?')}, completion={tu.get('completion_tokens', '?')}, cached={cached}, reasoning={reasoning}")
            
            if tcs:
                for tc in tcs:
                    print(f"    → {tc.get('name')}({json.dumps(tc.get('args', {}))})")
            if content:
                print(f"    Response text:")
                print(f"    ---")
                for line in content.split("\n"):
                    print(f"    {line}")
                print(f"    ---")

    # Graph-level error field
    print(f"\n  Graph error field: {root.get('error')}")
    print(f"  Graph status: {root.get('status')}")
