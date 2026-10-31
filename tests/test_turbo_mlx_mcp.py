"""End-to-end check of tools/turbo_mlx_mcp.py over real MCP stdio JSON-RPC (needs Turbo MLX + its models).
Run: python3 tests/test_turbo_mlx_mcp.py [outdir]"""
import json, subprocess, sys, tempfile, time
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "tools" / "turbo_mlx_mcp.py"
out = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp())
out.mkdir(parents=True, exist_ok=True)
p = subprocess.Popen([sys.executable, str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
n = 0

def rpc(method, params=None):
    global n; n += 1
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": n, "method": method, "params": params or {}}) + "\n"); p.stdin.flush()
    while True:
        m = json.loads(p.stdout.readline())
        if m.get("id") == n:
            return m

def call(name, **args):
    t = time.time(); r = rpc("tools/call", {"name": name, "arguments": args})["result"]
    text = r["content"][0]["text"]; imgs = [c for c in r["content"] if c["type"] == "image"]
    print(f"\n## {name} ({time.time()-t:.1f}s) error={r['isError']} previews={len(imgs)}\n{text[:700]}")
    return r, (json.loads(text) if not r["isError"] else None)

def check(cond, what):
    print(("PASS " if cond else "FAIL ") + what)
    if not cond: sys.exit(1)

init = rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}})
check(init["result"]["serverInfo"]["name"] == "turbo-mlx", "initialize")
p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
names = [t["name"] for t in rpc("tools/list")["result"]["tools"]]
check(set(names) == {"turbo_mlx_generate_image", "turbo_mlx_edit_image", "turbo_mlx_generate_video", "turbo_mlx_status"}, f"tools/list {names}")

_, s = call("turbo_mlx_status"); check(s["app_installed"] and s["models"], "status lists installed models")
r, img = call("turbo_mlx_generate_image", prompt="a blocky toy robot made of plastic bricks, studio photo",
              width=512, height=512, steps=4, seed=7, output=str(out / "img.png"))
check(img["status"] == "done" and Path(img["path"]).is_file() and r["content"][-1]["type"] == "image", "generate_image")
r, ed = call("turbo_mlx_edit_image", prompt="paint the robot gold", image=img["path"], steps=4, seed=8, output=str(out / "edit.png"))
check(ed["status"] == "done" and Path(ed["path"]).is_file(), "edit_image")
_, bad = call("turbo_mlx_edit_image", prompt="x", image="/nope.png"); check(bad is None, "edit_image rejects a missing file")
_, v = call("turbo_mlx_generate_video", prompt="the gold robot waves", image=ed["path"], width=512, height=512,
            frames=25, steps=4, seed=9, wait=False, output=str(out / "vid.mp4"))
check(v["status"] in ("queued", "running") and v["id"], "generate_video wait=false returns a job id")
_, mid = call("turbo_mlx_status", id=v["id"]); check(mid["status"] in ("queued", "running", "done"), "status by id while running")
_, fin = call("turbo_mlx_status", id=v["id"], wait_s=600)
check(fin["status"] == "done" and Path(fin["path"]).is_file() and fin["frames"] == 25, "generate_video finished")
_, c = call("turbo_mlx_generate_video", prompt="a slow pan over a city", width=512, height=512, seconds=4, steps=4, wait=False)
time.sleep(4); _, cx = call("turbo_mlx_status", cancel=c["id"])
print("cancel result status:", cx["status"])
_, s2 = call("turbo_mlx_status"); check(len(s2["jobs"]) >= 4, "status lists jobs")
p.stdin.close(); p.wait(30)
print("\nALL PASSED; outputs in", out)
