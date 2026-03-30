#!/usr/bin/env python3
"""Get system prompt and second AI response details."""
import json, subprocess, os, sys

os.chdir('/Users/psmeunin/Projects/configbp-ai')
env_path = '.env'
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, val = line.partition('=')
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

FETCH = '.agents/skills/langsmith-trace/scripts/fetch_trace.py'

def fetch(url):
    r = subprocess.run([sys.executable, FETCH, url, '--mode', 'raw'], capture_output=True, text=True)
    return json.loads(r.stdout)

# TRACE 2 - get full system prompt
data2 = fetch("https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/0c08bf7e-f751-485a-955d-3705e8568318/r")
msgs = data2['inputs']['messages'][0]

# System prompt
sys_msg = msgs[0]
if isinstance(sys_msg, dict) and sys_msg.get('kwargs'):
    print("=== SYSTEM PROMPT (full) ===")
    print(sys_msg['kwargs'].get('content', '')[:3000])
else:
    print("=== SYSTEM PROMPT ===")
    print(str(sys_msg)[:3000])

# AI message with tool calls (message index 2)
print("\n\n=== TRACE 2 - AI TOOL CALL MESSAGE (retry attempt) ===")
ai_retry = msgs[5]  # The second AI message that retried
if isinstance(ai_retry, dict) and ai_retry.get('kwargs'):
    k = ai_retry['kwargs']
    print(f"type: {k.get('type')}")
    print(f"content: {k.get('content', '')[:500]}")
    tcs = k.get('tool_calls', [])
    additional = k.get('additional_kwargs', {})
    for tc in tcs:
        print(f"tool_call: {tc.get('name')}({json.dumps(tc.get('args',{}))[:300]})")
    for tc in additional.get('tool_calls', []):
        fn = tc.get('function', {})
        print(f"tool_call(oai): {fn.get('name')}({fn.get('arguments', '')[:300]})")
    # response metadata
    rm = k.get('response_metadata', {})
    print(f"finish_reason: {rm.get('finish_reason')}")
    usage = rm.get('token_usage', {})
    print(f"tokens: {json.dumps(usage)[:300]}")

# Now check trace 1 - the second AI msg
print("\n\n=== TRACE 1 - SECOND AI MESSAGE (response to user) ===")
data1 = fetch("https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/042673d8-68f0-494f-8680-7b08dbc7c2e7/r")
msgs1 = data1['outputs']['messages']
ai_msgs = [m for m in msgs1 if isinstance(m, dict) and m.get('type') == 'ai']
if len(ai_msgs) >= 2:
    second_ai = ai_msgs[1]
    print(f"content: {second_ai.get('content', '')[:1000]}")
    rm = second_ai.get('response_metadata', {})
    print(f"finish_reason: {rm.get('finish_reason', 'N/A')}")
    usage = rm.get('token_usage', {})
    print(f"tokens: {json.dumps(usage)[:300]}")
    print(f"model: {rm.get('model_name', 'N/A')}")
    # Check if it had usage_metadata
    um = second_ai.get('usage_metadata', {})
    print(f"usage_metadata: {json.dumps(um)[:300]}")
    
# Check trace1 outputs_preview - it said "assessments-configuration-summary" which looks like a tag
print(f"\n\n=== TRACE 1 METADATA ===")
print(f"outputs_preview: {data1.get('outputs_preview', '')}")
print(f"tags: {data1.get('tags', [])}")
print(f"extra keys: {list(data1.get('extra', {}).keys())}")
extra = data1.get('extra', {})
metadata = extra.get('metadata', {})
print(f"metadata: {json.dumps(metadata, default=str)[:1000]}")

print(f"\n\n=== TRACE 2 METADATA ===")
print(f"outputs_preview: {data2.get('outputs_preview', '')}")
print(f"tags: {data2.get('tags', [])}")
extra2 = data2.get('extra', {})
metadata2 = extra2.get('metadata', {})
print(f"metadata: {json.dumps(metadata2, default=str)[:1000]}")

# Compare tool call patterns
print("\n\n=== RETRY COMPARISON ===")
print("Trace 1 (graph-level chain):")
print("  Step 1: AI calls 4 tools (query_findings x4) in parallel")
print("  Step 2: All 4 return MCPToolError")
print(f"  Step 3: AI responds to user: '{ai_msgs[1].get('content', '')[:200]}'")
print(f"  Total LLM calls: {len(ai_msgs)}")
print(f"  Retry behavior: No retry - gave up after first batch failure")

# Trace 2 had a retry
print("\nTrace 2 (LLM-level run):")
print("  Input shows the FULL conversation so far including:")
print("  - system prompt")
print("  - human message") 
print("  - AI call with 2 tools (query_findings x2)")
print("  - 2 tool errors")
print("  - AI RETRY call with 1 tool (query_findings)")
print("  - 1 more tool error")
print("  - This LLM call produces final response to user")
