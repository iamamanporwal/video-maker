"""python3 tex_pad.py out_dir [tex=1024]: _tex_src.npy + _tex_tris.json (from dump_mesh_uv.py) → robot_tex.png.
Dilates colour 16 px out of every UV island so downscaling/mipmaps never pull black gutter into seams, then resizes."""
import json, sys, os
import numpy as np
from PIL import Image, ImageDraw
out = sys.argv[1]; TEX = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
col = np.load(os.path.join(out, "_tex_src.npy")).astype(np.float32)
H, W = col.shape[:2]
cov = Image.new("L", (W, H), 0); d = ImageDraw.Draw(cov)
for t in json.load(open(os.path.join(out, "_tex_tris.json"))):
    d.polygon([(t[0] * W, t[1] * H), (t[2] * W, t[3] * H), (t[4] * W, t[5] * H)], fill=255)
mask = np.array(cov) > 0
aop = os.path.join(out, "_ao.npy")
if os.path.exists(aop):                       # bake_ao.py: multiply soft AO into albedo (Roblox has none on meshes)
    ao = np.array(Image.fromarray((np.load(aop) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
    STRENGTH = float(os.environ.get("AO_STRENGTH", "0.85"))
    col *= (1 - STRENGTH + STRENGTH * ao)[..., None]
    os.remove(aop)
print("uv coverage %.1f%%" % (100 * mask.mean()))
for _ in range(16):
    m3 = mask[..., None].astype(np.float32)
    acc = np.zeros_like(col); cnt = np.zeros(mask.shape + (1,), np.float32)
    for sh in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        acc += np.roll(col * m3, sh, (0, 1)); cnt += np.roll(m3, sh, (0, 1))
    grow = (~mask) & (cnt[..., 0] > 0)
    col[grow] = acc[grow] / cnt[grow]; mask |= grow
col[~mask] = col[mask].mean(axis=0)
Image.fromarray(col.astype(np.uint8)).resize((TEX, TEX), Image.LANCZOS).save(os.path.join(out, "robot_tex.png"))
for f in ("_tex_src.npy", "_tex_tris.json"): os.remove(os.path.join(out, f))
print("wrote", os.path.join(out, "robot_tex.png"))
