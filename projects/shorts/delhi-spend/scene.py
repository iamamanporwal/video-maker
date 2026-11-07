"""blender -b -P scene.py -- <out.blend>: "How much money can you spend in one day in Delhi?" (hypothetical, absurd).

Every key time is a VO word time from out/words.json (vo.py). Cast: Renderpeople Eric. Props: Sketchfab CC-BY
(assets/*.json). One Blender scene per set; sets_a.py / sets_b.py build them, this file wires header + save.

  GATE   0.00  hook: India Gate, cash rains on you            FOOD   6.64  chole bhature towers
  STREET 13.60 every auto rickshaw → gold wave                METRO  21.12 the Metro stops at your house
  POOL   28.08 butter-chicken pool, you jump in               GOLD   34.72 80 kg of gold, you sink
  BARAAT 41.84 dhol crowd + fireworks                         SMOG   49.12 Qutub-sized fan blows the smog away
  BANK   56.71 cash mountain, you buy the bank                VI3W   64.61 real sketch → real Vi3W model
"""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "src", "reelforge", "blender"))
sys.path.insert(0, HERE)
import bpy
import director as D
import look as L
import cast as C

out = sys.argv[sys.argv.index("--") + 1]
VO = json.load(open(os.path.join(HERE, "out", "words.json")))
B = VO["beats"]
W = {}
for a, b, w in VO["words"]:                             # first time each (lower, stripped) word is said
    W.setdefault(w.lower().strip(".,?!"), a)
END = VO["words"][-1][1] + 0.9
F = D.T
H = D.hex_lin
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
random.seed(7)

base = D.reset(frames=F(END) - 1)
D.fast_eevee(base, samples=12, look="AgX - Punchy")
SHOTS = []


def shot(sc, name, t0, t1, loc0, loc1, at0, at1, lens0=30, lens1=None, shake=0.005, dof=None):
    c, l = D.camera(name, lens0, dof=dof)
    D.move(c, l, F(t0), F(t1), loc0, loc1, at0, at1, lens0, lens1 or lens0)
    if shake:
        D.handheld(l, shake, seed=len(SHOTS))
    D.cut(sc, F(t0), c)
    SHOTS.append((sc.name, F(t0), F(t1) - 1 if t1 < END else F(END) - 1))


def studio(sc, colour, strength=0.9, key_w=450, at=(0, 0, 1.2), hdri="studio_small_09", y_wall=12):
    L.hdri_world(sc, hdri, strength, rot_deg=40, backdrop=colour, backdrop_strength=0.9)
    D.cyclorama(L.plastic(sc.name + "_cyc", colour, rough=0.72, coat=0.0), width=60 + 2 * y_wall, depth=40 + y_wall, y_wall=y_wall, radius=5,
                height=30)
    D.area_light(sc.name + "_key", key_w, (-3, -5, 6), at, size=4)
    D.area_light(sc.name + "_rim", key_w * 0.6, (3, 4, 4), at, size=3, rgb=H("#fff1dc"))


def txt(body, size, loc, m, rot=(math.pi / 2, 0, 0), extrude=0.05):
    return D.text3d("t_" + body[:12], body, size, loc, m, extrude=extrude, bevel=size * 0.035, font=FONT, rot=rot)


def pose(arm, root, keys, t1=None):
    """[(seconds, POSE), ...] → one held NLA strip to t1 (default END)."""
    C.pose_strip(arm, root, [(max(1, F(t)), p) for t, p in keys] + [(F(t1 or END), keys[-1][1])], 1, F(t1 or END),
                 blend=1)


MAT = {k: L.plastic(k, H(c), rough=r) for k, c, r in (
    ("white", "#f7f4ef", 0.3), ("ink", "#1f2230", 0.4), ("red", "#ff3b47", 0.3), ("yellow", "#ffc21a", 0.3),
    ("saffron", "#ff8a1f", 0.35), ("green", "#1fa34a", 0.35), ("cream", "#f3e3c3", 0.5))}
MAT["gold"] = C.gold_mat()
MAT["txt"] = L.plastic("txt", H("#ffffff"), rough=0.3, emit=H("#ffffff"), emit_strength=0.4)

ctx = dict(D=D, L=L, C=C, B=B, W=W, END=END, F=F, H=H, MAT=MAT, shot=shot, studio=studio, txt=txt, pose=pose,
           math=math, random=random, bpy=bpy, HERE=HERE)
for part in ("sets_a.py", "sets_b.py"):
    exec(open(os.path.join(HERE, part)).read(), ctx)

SHOTS.sort(key=lambda x: x[1])
json.dump(SHOTS, open(os.path.join(os.path.dirname(out), "shots.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out, "shots", len(SHOTS), "scenes", [s.name for s in bpy.data.scenes])
