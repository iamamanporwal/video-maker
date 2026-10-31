#!/usr/bin/env python3
"""Run a batch of Turbo MLX MCP tool calls from a JSON file through tools/turbo_mlx_mcp.py (same code path Claude Code
uses). Each item: {"tool": "turbo_mlx_generate_image" | ..., "args": {...}}. Items run in order; one line per result.
Usage: python3 tools/turbo_mlx_batch.py jobs.json"""
import json, subprocess, sys, time
from pathlib import Path

srv = subprocess.Popen([sys.executable, str(Path(__file__).with_name("turbo_mlx_mcp.py"))],
                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
n = 0
def rpc(method, params):
    global n; n += 1
    srv.stdin.write(json.dumps({"jsonrpc": "2.0", "id": n, "method": method, "params": params}) + "\n"); srv.stdin.flush()
    while True:
        m = json.loads(srv.stdout.readline())
        if m.get("id") == n: return m
rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "batch", "version": "0"}})
for job in json.load(open(sys.argv[1])):
    t = time.time()
    r = rpc("tools/call", {"name": job["tool"], "arguments": {"preview": False, **job["args"]}})["result"]
    text = r["content"][0]["text"]
    out = text if r["isError"] else json.loads(text).get("path")
    print(f"{'ERR' if r['isError'] else 'OK '} {time.time()-t:6.1f}s {out}", flush=True)
srv.stdin.close(); srv.wait(30)
