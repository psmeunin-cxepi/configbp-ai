#!/usr/bin/env python3
"""Analyze two LangSmith traces for error handling comparison."""
import sys
import json
import subprocess
import os

TRACE_URLS = {
    "trace1_detailed_error": "https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/042673d8-68f0-494f-8680-7b08dbc7c2e7/r",
    "trace2_general_error": "https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/0c08bf7e-f751-485a-955d-3705e8568318/r",
}

FETCH_SCRIPT = ".agents/skills/langsmith-trace/scripts/fetch_trace.py"

def fetch_trace(url):
    result = subprocess.run(
        ["python3", FETCH_SCRIPT, url, "--mode", "raw"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR fetching {url}: {result.stderr}", file=sys.stderr)
        return None
    return json.loads(result.stdout)

def flatten_msg(m):
    """Normalize a message that might be a dict or nested list."""
    if isinstance(m, dict):
        return m
    if isinstance(m, list):
        # Some traces wrap messages in a list-of-lists
        if len(m) > 0 and isinstance(m[0], dict):
            return m[0]
    return {'type': 'unknown', 'content': str(m)[:200]}

def analyze_trace(name, data):
    print(f"\n{'='*80}")
    print(f"TRACE: {name}")
    print(f"{'='*80}")
    
    print(f"Name: {data.get('name')}")
    print(f"Run type: {data.get('run_type')}")
    print(f"Status: {data.get('status')}")
    print(f"Error: {data.get('error')}")
    print(f"Start: {data.get('start_time')}")
    print(f"End: {data.get('end_time')}")
    print(f"Total tokens: {data.get('total_tokens')}")
    print(f"Prompt tokens: {data.get('prompt_tokens')}")
    print(f"Completion tokens: {data.get('completion_tokens')}")
    print(f"Tags: {data.get('tags')}")
    print(f"Inputs preview: {data.get('inputs_preview', '')[:300]}")
    print(f"Outputs preview: {data.get('outputs_preview', '')[:500]}")
    
    # Input
    inp = data.get('inputs', {})
    if isinstance(inp, dict):
        inp_msgs = inp.get('messages', [])
    else:
        inp_msgs = []
    
    print(f"\n--- INPUTS ({len(inp_msgs)} items) ---")
    for i, raw in enumerate(inp_msgs):
        m = flatten_msg(raw)
        mtype = m.get('type', m.get('role', '?'))
        content = str(m.get('content', ''))
        print(f"  [{i}] {mtype}: {content[:300]}")
    
    # Output
    out = data.get('outputs', {})
    if isinstance(out, dict):
        # Could be {"messages": [...]} or {"generations": [...]} or direct AI message
        out_msgs = out.get('messages', [])
        if not out_msgs:
            # LLM run format
            gens = out.get('generations', [])
            if gens:
                print(f"\n--- GENERATIONS ({len(gens)} groups) ---")
                for gi, gen_group in enumerate(gens):
                    if isinstance(gen_group, list):
                        for gj, gen in enumerate(gen_group):
                            text = gen.get('text', '')
                            msg = gen.get('message', {})
                            if isinstance(msg, dict):
                                content = msg.get('kwargs', {}).get('content', '') or text
                                tool_calls = msg.get('kwargs', {}).get('tool_calls', [])
                                additional = msg.get('kwargs', {}).get('additional_kwargs', {})
                                resp_meta = msg.get('kwargs', {}).get('response_metadata', {})
                                finish = resp_meta.get('finish_reason', 'N/A')
                                print(f"  [{gi}.{gj}] content: {str(content)[:400]}")
                                print(f"           finish_reason: {finish}")
                                if tool_calls:
                                    for tc in tool_calls:
                                        print(f"           tool_call: {tc.get('name','?')}({json.dumps(tc.get('args',{}))[:200]})")
                                if additional.get('tool_calls'):
                                    for tc in additional['tool_calls']:
                                        fn = tc.get('function', {})
                                        print(f"           tool_call(additional): {fn.get('name','?')}({str(fn.get('arguments',''))[:200]})")
                out_msgs = []  # handled via generations
    else:
        out_msgs = []
    
    if out_msgs:
        print(f"\n--- OUTPUT MESSAGES ({len(out_msgs)} messages) ---")
        for i, raw in enumerate(out_msgs):
            m = flatten_msg(raw)
            mtype = m.get('type', '?')
            content = str(m.get('content', ''))
            tool_calls = m.get('tool_calls', [])
            status = m.get('status', '')
            tool_name = m.get('name', '')
            
            extra = ''
            if mtype == 'tool':
                extra = f' [status={status}, name={tool_name}]'
            
            display = content[:500] + ('...' if len(content) > 500 else '')
            print(f"  [{i}] {mtype}{extra}: {display}")
            
            if tool_calls:
                for tc in tool_calls:
                    tc_name = tc.get('name', '?')
                    tc_args = json.dumps(tc.get('args', {}))[:300]
                    print(f"       -> tool_call: {tc_name}({tc_args})")
    
    # Look for the final AI message
    print(f"\n--- FINAL AI RESPONSE ---")
    found_final = False
    for raw in reversed(out_msgs):
        m = flatten_msg(raw)
        if m.get('type') == 'ai' and m.get('content'):
            print(f"  Content: {str(m.get('content',''))[:1000]}")
            print(f"  Finish reason: {m.get('response_metadata', {}).get('finish_reason', 'N/A')}")
            found_final = True
            break
    if not found_final:
        print(f"  (No final AI content message in output messages)")
    
    # Count tool calls and errors
    tool_calls_made = []
    tool_errors = []
    for raw in out_msgs:
        m = flatten_msg(raw)
        if m.get('type') == 'ai' and m.get('tool_calls'):
            for tc in m['tool_calls']:
                tool_calls_made.append(tc.get('name', '?'))
        if m.get('type') == 'tool':
            info = {
                'name': m.get('name', '?'),
                'status': m.get('status', 'ok'),
                'content_preview': str(m.get('content', ''))[:500],
            }
            if m.get('status') == 'error' or 'error' in str(m.get('content', '')).lower():
                tool_errors.append(info)
    
    print(f"\n--- TOOL CALL SUMMARY ---")
    print(f"  Tool calls made: {tool_calls_made}")
    print(f"  Tool errors: {len(tool_errors)}")
    for te in tool_errors:
        print(f"    - {te['name']} [status={te['status']}]: {te['content_preview'][:300]}")
    
    # Dump full raw outputs for deep analysis
    print(f"\n--- RAW OUTPUTS (truncated) ---")
    print(json.dumps(out, indent=2, default=str)[:3000])
    
    return {
        'name': data.get('name'),
        'run_type': data.get('run_type'),
        'status': data.get('status'),
        'out_msgs': out_msgs,
        'tool_calls_made': tool_calls_made,
        'tool_errors': tool_errors,
        'raw_outputs': out,
        'raw_inputs': data.get('inputs'),
        'inputs_preview': data.get('inputs_preview', ''),
        'outputs_preview': data.get('outputs_preview', ''),
    }

if __name__ == '__main__':
    # Source .env
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, val = line.partition('=')
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
    
    results = {}
    for name, url in TRACE_URLS.items():
        data = fetch_trace(url)
        if data:
            results[name] = analyze_trace(name, data)
        else:
            print(f"Failed to fetch {name}")
    
    # Comparison
    if len(results) == 2:
        print(f"\n{'='*80}")
        print("COMPARISON")
        print(f"{'='*80}")
        for name, r in results.items():
            print(f"\n{name}:")
            print(f"  Run type: {r['run_type']}")
            print(f"  Tool calls: {r['tool_calls_made']}")
            print(f"  Errors: {len(r['tool_errors'])}")
