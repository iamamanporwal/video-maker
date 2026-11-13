"""Minimal stdio MCP client for Roblox StudioMCP. usage: mcp.py list | mcp.py call <tool> '<json args>'"""
import json, subprocess, sys
p = subprocess.Popen(["/Applications/RobloxStudio.app/Contents/MacOS/StudioMCP"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
n = 0
def rpc(method, params=None, notify=False):
    global n
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None: msg["params"] = params
    if not notify: n += 1; msg["id"] = n
    p.stdin.write(json.dumps(msg) + "\n"); p.stdin.flush()
    if notify: return None
    while True:
        line = p.stdout.readline()
        if not line: raise SystemExit("server closed")
        r = json.loads(line)
        if r.get("id") == n: return r
rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "cli", "version": "1"}})
rpc("notifications/initialized", notify=True)
if sys.argv[1] == "list":
    for t in rpc("tools/list")["result"]["tools"]:
        print("##", t["name"], "-", t.get("description", "")[:300].replace("\n", " "))
        print("   args:", json.dumps(t.get("inputSchema", {}).get("properties", {}))[:600])
else:
    r = rpc("tools/call", {"name": sys.argv[2], "arguments": json.loads(sys.argv[3] if len(sys.argv) > 3 else "{}")})
    res = r.get("result", r)
    for c in res.get("content", []) if isinstance(res, dict) else []:
        if c.get("type") == "text": print(c["text"])
        elif c.get("type") == "image":
            import base64; out = sys.argv[4] if len(sys.argv) > 4 else "shot.png"
            open(out, "wb").write(base64.b64decode(c["data"])); print("saved", out)
    if "error" in r: print(json.dumps(r["error"]))
p.terminate()
