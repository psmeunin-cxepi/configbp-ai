#!/usr/bin/env python3
"""Dump full trace 2 input messages for analysis."""
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
    if r.returncode != 0:
        print('STDERR:', r.stderr[:500], file=sys.stderr)
        return None
    return json.loads(r.stdout)

# Trace 2 - the LLM-level run
url2 = "https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/0c08bf7e-f751-485a-955d-3705e8568318/r"
data2 = fetch(url2)
if not data2:
    print("Failed to fetch trace 2")
    sys.exit(1)

# Full input messages
inp = data2.get('inputs', {})
msgs = inp.get('messages', [])
print(f"=== TRACE 2 INPUT MESSAGES ({len(msgs)} groups) ===\n")
for i, group in enumerate(msgs):
    if isinstance(group, list):
        print(f"--- Group {i} ({len(group)} messages) ---")
        for j, m in enumerate(group):
            if isinstance(m, dict):
                mtype = m.get('type', m.get('role', '?'))
                content = m.get('content', '')
                kwargs = m.get('kwargs', {})
                if kwargs:
                    inner_content = kwargs.get('content', '')
                    inner_type = kwargs.get('type', '')
                    tool_calls = kwargs.get('tool_calls', [])
                    additional = kwargs.get('additional_kwargs', {})
                    print(f"  [{j}] type={inner_type or mtype}")
                    if inner_content:
                        print(f"      content: {str(inner_content)[:500]}")
                    if tool_calls:
                        for tc in tool_calls:
                            print(f"      tool_call: {tc.get('name','?')}({json.dumps(tc.get('args',{}))[:200]})")
                    if additional.get('tool_calls'):
                        for tc in additional['tool_calls']:
                            fn = tc.get('function', {})
                            print(f"      tool_call(oai): {fn.get('name','?')}({str(fn.get('arguments',''))[:200]})")
                    # Check for tool response status
                    if inner_type == 'tool':
                        status = kwargs.get('status', 'ok')
                        name = kwargs.get('name', '')
                        print(f"      status={status}, tool_name={name}")
                else:
                    print(f"  [{j}] type={mtype}: {str(content)[:500]}")
            else:
                print(f"  [{j}] (non-dict): {str(m)[:200]}")
    elif isinstance(group, dict):
        mtype = group.get('type', '?')
        print(f"--- Item {i}: type={mtype} ---")
        print(f"  {json.dumps(group, indent=2, default=str)[:500]}")
    else:
        print(f"--- Item {i}: {type(group)} ---")
        print(f"  {str(group)[:200]}")

print("\n\n=== TRACE 2 FULL OUTPUT ===\n")
out = data2.get('outputs', {})
print(json.dumps(out, indent=2, default=str)[:5000])

# Also get trace 1 full details for retry analysis
print("\n\n=== TRACE 1 DETAILS ===")
url1 = "https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/042673d8-68f0-494f-8680-7b08dbc7c2e7/r"
data1 = fetch(url1)
if data1:
    out1 = data1.get('outputs', {})
    msgs1 = out1.get('messages', [])
    # Check if there's a retry after the errors (second AI call)
    ai_msgs = [m for m in msgs1 if isinstance(m, dict) and m.get('type') == 'ai']
    print(f"\nAI messages count: {len(ai_msgs)}")
    for idx, ai_msg in enumerate(ai_msgs):
        tcs = ai_msg.get('tool_calls', [])
        content = ai_msg.get('content', '')
        finish = ai_msg.get('response_metadata', {}).get('finish_reason', 'N/A')
        print(f"\n  AI msg {idx}:")
        print(f"    content: {str(content)[:500]}")
        print(f"    finish_reason: {finish}")
        print(f"    tool_calls: {[tc.get('name') for tc in tcs]}")
        # Check usage metadata
        usage = ai_msg.get('usage_metadata', {})
        print(f"    tokens: in={usage.get('input_tokens', '?')}, out={usage.get('output_tokens', '?')}")
    
    # Output preview
    print(f"\n  Outputs preview: {data1.get('outputs_preview', '')[:500]}")
