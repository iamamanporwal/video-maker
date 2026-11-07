"""Heuristic humanoid auto-rig, inside Blender (no ML weights needed).

    Blender -b --factory-startup -P blender/autorig.py -- IN.glb OUT.glb [--strip] [--preview PNG]

1. imports a GLB/FBX/OBJ, keeps the visible meshes (an existing rig is removed with
   --strip, keeping its bind-pose geometry), joins them;
2. finds humanoid landmarks from the geometry - floor, crotch (where the legs merge),
   knees/ankles/toes per leg, the two most lateral points as finger tips, spine/neck/head
   along the body's centre - in a canonical frame (left = +X, up = +Z, forward = -Y; the
   facing is detected from which way the feet stick out);
3. builds a SOMA-named armature (Hips, Spine1, Spine2, Chest, Neck1, Head, Left/Right
   Shoulder, Arm, ForeArm, Hand, Leg, Shin, Foot, ToeBase) so Kimodo motion maps 1:1;
4. skins with Blender's heat-diffusion automatic weights, falling back to distance-to-bone
   weights for vertices heat-diffusion leaves unweighted (common on non-manifold meshes);
5. exports a rigged GLB (+ a rig.json of joints/report).

This is the zero-download fallback. SkinTokens (skintokens-cli) is the ML rigger and is
selected in pipeline.py with --rigger skintokens.
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, DST = Path(argv[0]), Path(argv[1])
STRIP = "--strip" in argv
PREVIEW = Path(argv[argv.index("--preview") + 1]) if "--preview" in argv else None

bpy.ops.wm.read_factory_settings(use_empty=True)


def import_any(p: Path):
    ext = p.suffix.lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(p))
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(p))
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=str(p))
    else:
        raise SystemExit(f"unsupported input {ext}")


import_any(SRC)

# ------------------------------------------------------------------ collect meshes
shape_objs = {pb.custom_shape for o in bpy.data.objects if o.type == "ARMATURE"
              for pb in o.pose.bones if pb.custom_shape}
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o not in shape_objs]
for o in shape_objs:
    bpy.data.objects.remove(o)
if arms and not STRIP:
    raise SystemExit("input already has an armature - pass --strip to re-rig, or skip rigging")
for m in meshes:
    for mod in list(m.modifiers):
        if mod.type == "ARMATURE":
            m.modifiers.remove(mod)
    m.vertex_groups.clear()
    mw = m.matrix_world.copy()
    m.parent = None
    m.matrix_world = mw
for a in arms:
    bpy.data.objects.remove(a)
for o in list(bpy.data.objects):
    if o.type == "EMPTY":
        bpy.data.objects.remove(o)

bpy.ops.object.select_all(action="DESELECT")
for m in meshes:
    m.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
body.name = "Body"

V = np.array([v.co[:] for v in body.data.vertices])
# Landmarks are measured on points sampled evenly over the surface (area-weighted), not on
# raw vertices: low-poly meshes have too few vertices per cross-section to measure widths.
body.data.calc_loop_triangles()
tri = np.array([t.vertices[:] for t in body.data.loop_triangles])
A, B, Cc = V[tri[:, 0]], V[tri[:, 1]], V[tri[:, 2]]
area = 0.5 * np.linalg.norm(np.cross(B - A, Cc - A), axis=1)
rng = np.random.default_rng(0)
pick = rng.choice(len(tri), size=80000, p=area / area.sum())
u, v_ = rng.random(80000), rng.random(80000)
flip = u + v_ > 1
u[flip], v_[flip] = 1 - u[flip], 1 - v_[flip]
P = A[pick] + u[:, None] * (B[pick] - A[pick]) + v_[:, None] * (Cc[pick] - A[pick])
zmin, zmax = V[:, 2].min(), V[:, 2].max()
H = zmax - zmin

# ------------------------------------------------------------------ canonical frame
# forward: toes stick out of the ankle in the walking direction
low = P[P[:, 2] < zmin + 0.035 * H]
ank = P[(P[:, 2] > zmin + 0.07 * H) & (P[:, 2] < zmin + 0.12 * H)]
d = low[:, 1].mean() - ank[:, 1].mean() if len(low) and len(ank) else -1.0
fwd_sign = -1.0 if d <= 0 else 1.0           # -Y is glTF's +Z forward
# canonical coords: x = character's left, y = forward(-), z = up.  If the model faces +Y
# its left is -X, so mirror both horizontal axes (a 180 deg turn about Z).
F = np.diag([1.0, 1.0, 1.0]) if fwd_sign < 0 else np.diag([-1.0, -1.0, 1.0])
C = P @ F.T                                   # canonical surface samples
x, y, z = C[:, 0], C[:, 1], C[:, 2]
zr = z - zmin                                  # height above floor


def band(lo, hi, mask=None):
    m = (zr >= lo * H) & (zr <= hi * H)
    return m if mask is None else m & mask


torso = band(0.45, 0.65)
cx = float(np.median(x[torso]))
half_w = float(np.percentile(np.abs(x[torso] - cx), 90))

# crotch: lowest height where the slice is continuous across the body centre
# Measured as surface density in a thin centre strip relative to the leg strips, so legs
# that nearly touch (baggy trousers, scans) do not read as a closed crotch.
crotch = None
for h in np.arange(0.30, 0.62, 0.005):
    s = band(h - 0.006, h + 0.006)
    xs = x[s] - cx
    centre = np.sum(np.abs(xs) < 0.012 * H)
    legs_d = max(np.sum(np.abs(xs - 0.05 * H) < 0.012 * H), np.sum(np.abs(xs + 0.05 * H) < 0.012 * H), 1)
    if centre > 0.35 * legs_d and h > 0.36:
        crotch = h
        break
crotch = crotch if crotch is not None else 0.47
report = {"height_m": float(H), "facing": "-Y" if fwd_sign < 0 else "+Y", "crotch_rel": float(crotch)}


def centroid(mask):
    if mask.sum() == 0:
        return None
    return C[mask].mean(0)


def near(p, r):
    """centroid of vertices within r of p (keeps joints inside the mesh)"""
    m = np.linalg.norm(C - p, axis=1) < r
    return C[m].mean(0) if m.sum() > 3 else p


def core_half_width(h, tol=0.006):
    """Half-width of the body's central connected run at height h (arms separated from
    the torso by a gap are excluded)."""
    s = band(h - tol, h + tol)
    d = np.sort(np.abs(x[s] - cx))
    if len(d) == 0 or d[0] > 0.03 * H:
        return 0.0
    gaps = np.where(np.diff(d) > 0.02 * H)[0]
    return float(d[gaps[0]] if len(gaps) else d[-1])


# neck = narrowest central cross-section between chest and head (works for stylised
# proportions where fixed ratios fail, e.g. big-headed characters)
hs = np.arange(crotch + 0.22, 0.90, 0.005)   # stop below the crown (heads taper too)
ws = np.array([core_half_width(h) for h in hs])
ws_s = np.convolve(ws, np.ones(3) / 3, mode="same")
valid = ws_s > 0
neck_h = float(hs[valid][np.argmin(ws_s[valid])]) if valid.any() else 0.85
shoulder_h = neck_h - 0.045
chest_w = core_half_width(shoulder_h - 0.08)
sh_off_base = float(np.clip(0.9 * chest_w, 0.06 * H, 0.14 * H)) if chest_w > 0 else 0.105 * H
report.update(neck_rel=neck_h, shoulder_rel=shoulder_h)

J = {}
for side, sgn in (("Left", 1), ("Right", -1)):
    leg = (sgn * (x - cx) > 0)
    upper = centroid(band(crotch - 0.05, crotch - 0.02, leg))
    ankle = centroid(band(0.045, 0.075, leg))
    hip_z = zmin + (crotch + 0.035) * H
    J[f"{side}Leg"] = np.array([upper[0], upper[1], hip_z])
    knee_z = ankle[2] + 0.5 * (hip_z - ankle[2]) + 0.01 * H
    J[f"{side}Shin"] = centroid(band((knee_z - zmin) / H - 0.012, (knee_z - zmin) / H + 0.012, leg))
    J[f"{side}Foot"] = np.array([ankle[0], ankle[1], zmin + 0.045 * H])
    foot = band(0.0, 0.03, leg)
    tip_y = np.percentile(y[foot], 2)          # forward is -y in canonical frame
    toe_end = np.array([C[foot][:, 0].mean(), tip_y, zmin + 0.012 * H])
    J[f"{side}ToeBase"] = J[f"{side}Foot"] + 0.68 * (toe_end - J[f"{side}Foot"])
    J[f"{side}ToeBase"][2] = zmin + 0.015 * H
    J[f"{side}ToeEnd"] = toe_end

    # arm: finger tip = most lateral vertices above the crotch
    up = (zr > crotch * H) & (sgn * (x - cx) > 0)
    lat = sgn * (x - cx)
    thr = np.percentile(lat[up], 99.5)
    tip = C[up & (lat >= thr)].mean(0)
    sh_z = zmin + shoulder_h * H
    chest_y = centroid(band(shoulder_h - 0.03, shoulder_h + 0.01, np.abs(x - cx) < 0.06 * H))[1]
    sh_off = min(sh_off_base, 0.75 * abs(tip[0] - cx))
    shoulder = np.array([cx + sgn * sh_off, chest_y, sh_z])
    arm_len = np.linalg.norm(tip - shoulder)
    arm_dir = (tip - shoulder) / arm_len
    wrist = tip - 0.22 * arm_len * arm_dir
    elbow = near(0.5 * (shoulder + wrist), 0.035 * H)
    J[f"{side}Shoulder"] = np.array([cx + sgn * 0.02 * H, chest_y, sh_z - 0.01 * H])
    J[f"{side}Arm"] = shoulder
    J[f"{side}ForeArm"] = elbow
    J[f"{side}Hand"] = wrist
    J[f"{side}HandEnd"] = tip
    report[f"{side}_hand_tip"] = tip.round(3).tolist()


def spine_pt(h):
    c = centroid(band(h - 0.01, h + 0.01, np.abs(x - cx) < 0.06 * H))
    return np.array([cx, c[1] if c is not None else 0.0, zmin + h * H])


hips_h = crotch + 0.05
neck_base = shoulder_h + 0.01
for name, f in (("Hips", 0.0), ("Spine1", 0.25), ("Spine2", 0.5), ("Chest", 0.75)):
    J[name] = spine_pt(hips_h + f * (neck_base - hips_h))
J["Neck1"] = spine_pt(neck_base)
J["Head"] = spine_pt(min(neck_h + 0.02, 0.97))
J["HeadEnd"] = np.array([cx, J["Head"][1], zmax])

# ------------------------------------------------------------------ armature
BONES = [  # name, parent, tail joint
    ("Hips", None, "Spine1"), ("Spine1", "Hips", "Spine2"), ("Spine2", "Spine1", "Chest"),
    ("Chest", "Spine2", "Neck1"), ("Neck1", "Chest", "Head"), ("Head", "Neck1", "HeadEnd"),
]
for s in ("Left", "Right"):
    BONES += [
        (f"{s}Shoulder", "Chest", f"{s}Arm"), (f"{s}Arm", f"{s}Shoulder", f"{s}ForeArm"),
        (f"{s}ForeArm", f"{s}Arm", f"{s}Hand"), (f"{s}Hand", f"{s}ForeArm", f"{s}HandEnd"),
        (f"{s}Leg", "Hips", f"{s}Shin"), (f"{s}Shin", f"{s}Leg", f"{s}Foot"),
        (f"{s}Foot", f"{s}Shin", f"{s}ToeBase"), (f"{s}ToeBase", f"{s}Foot", f"{s}ToeEnd"),
    ]

Finv = F.T  # canonical -> world (F is orthogonal and its own inverse here)
W = {k: Finv @ v for k, v in J.items()}

arm_data = bpy.data.armatures.new("Rig")
rig = bpy.data.objects.new("Rig", arm_data)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
eb = {}
for name, parent, tail in BONES:
    b = arm_data.edit_bones.new(name)
    b.head, b.tail = Vector(W[name]), Vector(W[tail])
    if parent:
        b.parent = eb[parent]
        b.use_connect = False
    eb[name] = b
# consistent roll: bone Z axis towards the character's forward
fwd = Vector((0, -1, 0)) if fwd_sign < 0 else Vector((0, 1, 0))
for b in eb.values():
    b.align_roll(fwd if abs(b.vector.normalized().dot(fwd)) < 0.9 else Vector((0, 0, 1)))
bpy.ops.object.mode_set(mode="OBJECT")

# ------------------------------------------------------------------ skinning
# Scanned / game meshes are split along UV and material seams (duplicate vertices at the
# same position). Heat weighting treats each island separately, so the two sides of a seam
# get different weights and tear open when a joint bends (gaps at shoulders and elbows). So:
# weight a welded copy, smooth the weights, then copy them back by position.
import bmesh  # noqa: E402

weld = body.copy()
weld.data = body.data.copy()
weld.name = "BodyWelded"
bpy.context.collection.objects.link(weld)
bm = bmesh.new()
bm.from_mesh(weld.data)
before = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002 * H)
report["seam_vertices_welded"] = before - len(bm.verts)
bm.to_mesh(weld.data)
bm.free()

bpy.ops.object.select_all(action="DESELECT")
weld.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
bpy.ops.object.select_all(action="DESELECT")
weld.select_set(True)
bpy.context.view_layer.objects.active = weld
bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
bpy.ops.object.vertex_group_smooth(group_select_mode="ALL", factor=0.5, repeat=3)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.mode_set(mode="OBJECT")

bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type="ARMATURE_NAME")      # empty groups + armature modifier
dt = body.modifiers.new("weights", "DATA_TRANSFER")
dt.object = weld
dt.use_vert_data = True
dt.data_types_verts = {"VGROUP_WEIGHTS"}
dt.vert_mapping = "NEAREST"
dt.layers_vgroup_select_src = "ALL"
dt.layers_vgroup_select_dst = "NAME"
bpy.context.view_layer.objects.active = body
bpy.ops.object.modifier_move_to_index(modifier="weights", index=0)
bpy.ops.object.modifier_apply(modifier="weights")
bpy.data.objects.remove(weld)

names = [n for n, _, _ in BONES]
groups = {g.index: g.name for g in body.vertex_groups}
tot = np.zeros(len(V))
for v in body.data.vertices:
    tot[v.index] = sum(g.weight for g in v.groups if groups.get(g.group) in names)
bad = np.where(tot < 1e-4)[0]
report["heat_unweighted_vertices"] = int(len(bad))
if len(bad):
    # fallback: inverse-distance to the 2 nearest bone segments
    seg = [(W[n], W[t]) for n, _, t in BONES]
    for i in bad:
        p = V[i]
        ds = []
        for a, b in seg:
            ab = b - a
            t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1)
            ds.append(np.linalg.norm(p - (a + t * ab)))
        ds = np.array(ds)
        k = np.argsort(ds)[:2]
        w = 1.0 / (ds[k] + 1e-3) ** 4
        w /= w.sum()
        for bi, wi in zip(k, w):
            vg = body.vertex_groups.get(names[bi]) or body.vertex_groups.new(name=names[bi])
            vg.add([int(i)], float(wi), "REPLACE")
report["joints_world"] = {k: np.round(v, 4).tolist() for k, v in W.items()}

# ------------------------------------------------------------------ export
DST.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
rig.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(DST), export_format="GLB", use_selection=True,
                          export_animations=False, export_skins=True)
Path(DST.with_suffix(".rig.json")).write_text(json.dumps(report, indent=1))
print("[autorig] wrote", DST, "| unweighted after heat:", len(bad), "| facing", report["facing"])

# ------------------------------------------------------------------ preview (front + side)
if PREVIEW:
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = 900, 900
    sc.display.shading.show_xray = True
    sc.display.shading.xray_alpha = 0.35
    mat = bpy.data.materials.new("bone")
    mat.diffuse_color = (1, 0.35, 0.05, 1)
    for n, _, t in BONES:
        a, b = Vector(W[n]), Vector(W[t])
        bpy.ops.mesh.primitive_cylinder_add(radius=0.012 * H, depth=(b - a).length,
                                            location=(a + b) / 2)
        c = bpy.context.object
        c.rotation_mode = "QUATERNION"
        c.rotation_quaternion = Vector((0, 0, 1)).rotation_difference((b - a).normalized())
        c.data.materials.append(mat)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.02 * H, location=a)
        bpy.context.object.data.materials.append(mat)
    sc.display.shading.color_type = "MATERIAL"
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.15 * max(H, float(np.ptp(V[:, 0])))
    ctr = Vector(((V[:, 0].max() + V[:, 0].min()) / 2, (V[:, 1].max() + V[:, 1].min()) / 2, zmin + H / 2))
    for tag, off in (("front", Vector((0, 5 * fwd_sign, 0))), ("side", Vector((5, 0, 0)))):
        cam.location = ctr + off
        cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(PREVIEW.with_name(PREVIEW.stem + f"_{tag}.png"))
        bpy.ops.render.render(write_still=True)
