#!/usr/bin/env python3
"""Fetch all 3 traces and save to /tmp for analysis."""
import json, subprocess, os, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")

# Load .env
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ[k.strip()] = v.strip().strip('"')

traces = {
    "trace1": "https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/2ae7e864-c303-4aca-b721-40f8f61d4a6c/r/019d303b-065c-7b42-9f88-975f1c09547c",
    "trace2": "https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/042673d8-68f0-494f-8680-7b08dbc7c2e7/r",
    "trace3": "https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/90507c0a-3d28-415f-93dc-e68aec2fcd26/r",
}

script = ".agents/skills/langsmith-trace/scripts/fetch_trace.py"

for name, url in traces.items():
    out = f"/tmp/{name}.json"
    print(f"Fetching {name}...")
    result = subprocess.run(
        [sys.executable, script, url, "--mode", "raw"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:200]}")
        continue
    with open(out, "w") as f:
        f.write(result.stdout)
    data = json.loads(result.stdout)
    # Check structure
    if "root" in data:
        rt = data["root"]["run_type"]
        name_val = data["root"]["name"]
        n_children = len(data.get("children", []))
        size = len(result.stdout)
        print(f"  OK: run_type={rt}, name={name_val}, children={n_children}, {size} bytes")
    else:
        rt = data.get("run_type", "?")
        name_val = data.get("name", "?")
        size = len(result.stdout)
        print(f"  OK: run_type={rt}, name={name_val} (no children wrapper), {size} bytes")
    print(f"  Saved to {out}")

print("\nDone.")
