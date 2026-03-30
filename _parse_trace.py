#!/usr/bin/env python3
"""Fetch and display any LangSmith public trace.

Usage:
    python3 _parse_trace.py <trace_url_or_share_token>

Examples:
    python3 _parse_trace.py https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/abcd1234-.../r
    python3 _parse_trace.py abcd1234-5678-...
"""
import json, sys, re, urllib.request, os
from datetime import datetime

API_KEY = os.environ.get("LANGSMITH_API_KEY", "")

# ---------------------------------------------------------------------------
# Parse input — accept full URL or bare share token
# ---------------------------------------------------------------------------
def parse_args():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    raw = sys.argv[1].strip().rstrip("/")

    # Extract base URL and share token from a full URL
    # e.g. https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/<token>/r
    m = re.match(r"(https?://[^/]+)/public/([0-9a-f-]+)", raw)
    if m:
        base = m.group(1) + "/api/v1"
        token = m.group(2)
    else:
        # Assume bare token; use LANGSMITH_ENDPOINT or default
        endpoint = os.environ.get("LANGSMITH_ENDPOINT", "https://langsmith.prod.usw2.plat.cxp.csco.cloud/api/v1")
        base = endpoint.rstrip("/")
        token = raw
    return base, token

BASE, SHARE_TOKEN = parse_args()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fetch(url):
    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def duration_str(start, end):
    if not (start and end):
        return ""
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return f" ({(e - s).total_seconds():.2f}s)"
    except Exception:
        return ""


def print_run(data, indent=0):
    pfx = "  " * indent
    name = data.get("name", "?")
    run_type = data.get("run_type", "?")
    status = data.get("status", "?")
    start = data.get("start_time", "")
    end = data.get("end_time", "")
    error = data.get("error")
    dur = duration_str(start, end)

    icon = {"success": "✓", "error": "✗"}.get(status, "⋯")
    print(f"{pfx}{icon} [{run_type}] {name}{dur}")

    if error:
        print(f"{pfx}  ERROR: {error[:300]}")

    total_tokens = data.get("total_tokens")
    if total_tokens:
        print(f"{pfx}  Tokens: {data.get('prompt_tokens', 0)} in / {data.get('completion_tokens', 0)} out / {total_tokens} total")

    cost = data.get("total_cost")
    if cost:
        print(f"{pfx}  Cost: ${cost:.6f}")

    if data.get("first_token_time") and start:
        try:
            s = datetime.fromisoformat(start.replace("Z", "+00:00"))
            ft = datetime.fromisoformat(data["first_token_time"].replace("Z", "+00:00"))
            print(f"{pfx}  TTFT: {(ft - s).total_seconds():.2f}s")
        except Exception:
            pass


def print_tool_calls(data, indent=0):
    """Extract and print tool calls from LLM outputs."""
    pfx = "  " * indent
    outputs = data.get("outputs") or {}
    generations = outputs.get("generations", [[]])
    for gen_group in generations:
        for gen in gen_group:
            msg = gen.get("message", {}).get("kwargs", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            if content:
                print(f"{pfx}Content: {content[:1500]}")
            if tool_calls:
                print(f"{pfx}Tool calls:")
                for tc in tool_calls:
                    print(f"{pfx}  → {tc.get('name', '?')}({json.dumps(tc.get('args', {}), indent=2)[:600]})")


def walk_children(share_token, run_data, indent=1):
    """Recursively fetch and print child runs."""
    child_ids = run_data.get("direct_child_run_ids") or run_data.get("child_run_ids") or []
    for cid in child_ids:
        try:
            child = fetch(f"{BASE}/public/{share_token}/run/{cid}")
            print_run(child, indent=indent)
            if child.get("run_type") == "llm":
                print_tool_calls(child, indent=indent + 1)
            walk_children(share_token, child, indent=indent + 1)
        except Exception as e:
            print(f"{'  ' * indent}  ⚠ Could not fetch child {cid}: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
print("=" * 70)
print("LANGSMITH TRACE ANALYSIS")
print("=" * 70)

root = fetch(f"{BASE}/public/{SHARE_TOKEN}/run")

# Metadata
extra = root.get("extra", {})
metadata = extra.get("metadata", {})
invocation = extra.get("invocation_params", {})

print(f"\nModel: {metadata.get('ls_model_name', invocation.get('model', 'N/A'))}")
print(f"Provider: {metadata.get('ls_provider', 'N/A')}")
print(f"Temperature: {invocation.get('temperature', 'N/A')}")
print(f"Trace ID: {root.get('trace_id', 'N/A')}")
print(f"Run ID: {root.get('id', 'N/A')}")
print(f"Tags: {root.get('tags', [])}")

# Run tree
print(f"\nRUN TREE:")
print("-" * 50)
print_run(root)
if root.get("run_type") == "llm":
    print_tool_calls(root, indent=1)
walk_children(SHARE_TOKEN, root)

# Inputs
print("\n" + "=" * 70)
print("INPUTS")
print("=" * 70)
print(root.get("inputs_preview", "N/A")[:2000])

# Outputs
print("\n" + "=" * 70)
print("OUTPUTS")
print("=" * 70)
preview = root.get("outputs_preview", "")
if preview:
    print(preview[:3000])
else:
    print_tool_calls(root)

# Token summary
print("\n" + "=" * 70)
print("TOKEN SUMMARY")
print("=" * 70)
llm_output = (root.get("outputs") or {}).get("llm_output", {})
tu = llm_output.get("token_usage", {})
if tu:
    cached = (tu.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    reasoning = (tu.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
    print(f"Prompt tokens: {tu.get('prompt_tokens', 'N/A')}  (cached: {cached})")
    print(f"Completion tokens: {tu.get('completion_tokens', 'N/A')}  (reasoning: {reasoning})")
    print(f"Total tokens: {tu.get('total_tokens', 'N/A')}")
print(f"Total cost: {root.get('total_cost', 'N/A')}")
model = llm_output.get("model_name", metadata.get("ls_model_name", "N/A"))
print(f"Model: {model}")
