#!/usr/bin/env python3
"""Extract key analysis data from all 3 traces."""
import json, sys

def load(path):
    with open(path) as f:
        return json.load(f)

def seconds_between(start, end):
    if not (start and end):
        return None
    from datetime import datetime
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return round((e - s).total_seconds(), 1)
    except:
        return None

def analyze_trace(path, label):
    data = load(path)
    root = data["root"]
    children = data.get("children", [])

    print(f"\n{'='*80}")
    print(f" {label}")
    print(f"{'='*80}")

    # Metadata
    meta = root.get("extra", {}).get("metadata", {})
    print(f"\nName: {root.get('name')}")
    print(f"Status: {root.get('status')}")
    print(f"Run type: {root.get('run_type')}")
    dur = seconds_between(root.get("start_time"), root.get("end_time"))
    print(f"Duration: {dur}s")
    print(f"Revision: {meta.get('revision_id', 'N/A')}")
    print(f"Tokens: prompt={root.get('prompt_tokens')}, completion={root.get('completion_tokens')}, total={root.get('total_tokens')}")
    ptd = root.get("prompt_token_details", {})
    ctd = root.get("completion_token_details", {})
    print(f"Cache read: {ptd.get('cache_read', 0)}, Reasoning: {ctd.get('reasoning', 0)}")

    # Children summary
    print(f"\nDirect children ({len(children)}):")
    for c in children:
        if c.get("fetch_error"):
            print(f"  FETCH ERROR: {c['fetch_error']}")
            continue
        cdur = seconds_between(c.get("start_time"), c.get("end_time"))
        print(f"  - {c.get('name')} (run_type={c.get('run_type')}, status={c.get('status')}, dur={cdur}s, tokens={c.get('total_tokens', 0)})")

    # Message flow from root.outputs.messages
    msgs = root.get("outputs", {}).get("messages", [])
    print(f"\nMessage flow ({len(msgs)} messages):")

    ai_calls_count = 0
    tool_error_count = 0
    tool_ok_count = 0
    ai_responses = []
    tool_calls_detail = []
    retry_cycles = 0
    last_was_tool_error = False

    for i, msg in enumerate(msgs):
        mtype = msg.get("type", "?")
        if mtype == "human":
            print(f"  [{i}] HUMAN: {msg.get('content', '')[:100]}")
        elif mtype == "ai":
            ai_calls_count += 1
            tcs = msg.get("tool_calls", [])
            content = msg.get("content", "")
            rm = msg.get("response_metadata", {})
            finish = rm.get("finish_reason", "?")
            model = rm.get("model_name", "?")
            tu = rm.get("token_usage", {})
            
            if tcs:
                if last_was_tool_error:
                    retry_cycles += 1
                print(f"  [{i}] AI (finish={finish}, model={model}): {len(tcs)} tool calls")
                for tc in tcs:
                    args_str = json.dumps(tc.get("args", {}))
                    print(f"        → {tc.get('name')}({args_str})")
                    tool_calls_detail.append(tc)
            else:
                print(f"  [{i}] AI RESPONSE (finish={finish}): {content[:200]}")
                ai_responses.append(content)
            last_was_tool_error = False

            # Token details if present
            if tu:
                cached = (tu.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
                reasoning = (tu.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
                print(f"        tokens: p={tu.get('prompt_tokens')}, c={tu.get('completion_tokens')}, cached={cached}, reasoning={reasoning}")

        elif mtype == "tool":
            status = msg.get("status", "")
            name = msg.get("name", "?")
            content = msg.get("content", "")[:150]
            if status == "error":
                tool_error_count += 1
                print(f"  [{i}] TOOL ERROR ({name}): {content}")
                last_was_tool_error = True
            else:
                tool_ok_count += 1
                print(f"  [{i}] TOOL OK ({name}): {content[:80]}...")
                last_was_tool_error = False

    # Summary
    print(f"\n--- Summary ---")
    print(f"AI calls: {ai_calls_count}")
    print(f"Tool calls total: {len(tool_calls_detail)}")
    print(f"Tool errors: {tool_error_count}")
    print(f"Tool successes: {tool_ok_count}")
    print(f"Retry cycles: {retry_cycles}")
    print(f"Final AI response:")
    for resp in ai_responses:
        print(f"  \"{resp}\"")

    # Extra outputs
    eo = root.get("outputs", {}).get("effective_intent")
    ft = root.get("outputs", {}).get("flow_type")
    if eo or ft:
        print(f"Effective intent: {eo}, Flow type: {ft}")

    # Model info from first llm child
    for c in children:
        if c.get("run_type") == "llm" or (c.get("extra", {}).get("invocation_params")):
            inv = c.get("extra", {}).get("invocation_params", {})
            cmeta = c.get("extra", {}).get("metadata", {})
            if inv.get("model") or cmeta.get("ls_model_name"):
                print(f"\nModel config (from child '{c.get('name')}'):")
                print(f"  model: {cmeta.get('ls_model_name', inv.get('model', 'N/A'))}")
                print(f"  temperature: {cmeta.get('ls_temperature', inv.get('temperature', 'N/A'))}")
                print(f"  max_tokens: {inv.get('max_tokens', 'N/A')}")
                break

    # Check for llm children nested inside chain children
    for c in children:
        if c.get("run_type") == "chain":
            # Check if this chain child has its own children with llm data
            child_child_ids = c.get("direct_child_run_ids", [])
            if child_child_ids:
                print(f"\n  Chain child '{c.get('name')}' has {len(child_child_ids)} sub-children (not fetched)")

    return {
        "label": label,
        "status": root.get("status"),
        "duration": dur,
        "total_tokens": root.get("total_tokens"),
        "ai_calls": ai_calls_count,
        "tool_calls": len(tool_calls_detail),
        "tool_errors": tool_error_count,
        "retry_cycles": retry_cycles,
        "final_response": ai_responses[-1] if ai_responses else "",
        "children_count": len(children),
    }

# Run all 3
results = []
results.append(analyze_trace("/tmp/trace1.json", "TRACE 1"))
results.append(analyze_trace("/tmp/trace2.json", "TRACE 2"))
results.append(analyze_trace("/tmp/trace3.json", "TRACE 3"))

print(f"\n{'='*80}")
print(" COMPARISON TABLE")
print(f"{'='*80}")
print(f"{'Metric':<30} {'Trace 1':<20} {'Trace 2':<20} {'Trace 3':<20}")
print("-" * 90)
for key in ["status", "duration", "total_tokens", "ai_calls", "tool_calls", "tool_errors", "retry_cycles", "children_count"]:
    vals = [str(r[key]) for r in results]
    print(f"{key:<30} {vals[0]:<20} {vals[1]:<20} {vals[2]:<20}")

print(f"\n{'='*80}")
print(" FINAL RESPONSES COMPARISON")
print(f"{'='*80}")
for r in results:
    print(f"\n{r['label']}:")
    print(f"  \"{r['final_response'][:300]}\"")
