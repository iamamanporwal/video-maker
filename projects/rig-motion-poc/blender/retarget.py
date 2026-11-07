"""Retarget a SOMA-77 motion (Kimodo NPZ) onto any rigged humanoid GLB/FBX, export animated GLB.

    Blender -b --factory-startup -P blender/retarget.py -- RIG.glb MOTION.npz OUT.glb [--preview DIR]

Maths (all in armature space, world-space rotations, so bone naming/roll/hierarchy depth
of the target does not matter):

    A        3x3 taking SOMA axes (left, up, forward) to the rig's (left, up, forward)
    G_j(t)   SOMA joint j's world rotation relative to SOMA's T-pose
    C_b      rest correction: swings target limb bone b so it points where SOMA's matching
             bone points in T-pose (fixes A-pose / odd rest poses)
    W_b(t) = A G_j(t) A^T C_b                     target world rotation
    basis  = R_b^T W_parent^T W_b R_b             Blender pose-bone rotation (R_b = rest)

Unmapped bones inherit their parent's W (identity basis). Hips travel is scaled by the
hip-height ratio so short characters do not moonwalk.

Bone mapping: SOMA names, then common aliases (Mixamo, SMPL, VRM/Unity humanoid), then a
topology matcher for unnamed rigs (e.g. SkinTokens' bone_0..N).
"""

import json
import re
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rigmotion.soma import AIM, BODY, IDX, SOMA77_PARENTS, load_motion, mat_to_quat, rotation_between, tpose  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
RIG, MOTION, OUT = Path(argv[0]), Path(argv[1]), Path(argv[2])
PREVIEW = Path(argv[argv.index("--preview") + 1]) if "--preview" in argv else None

bpy.ops.wm.read_factory_settings(use_empty=True)
ext = RIG.suffix.lower()
if ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=str(RIG))
elif ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=str(RIG), automatic_bone_orientation=False)
else:
    raise SystemExit(f"unsupported rig {ext}")

shape_objs = {pb.custom_shape for o in bpy.data.objects if o.type == "ARMATURE"
              for pb in o.pose.bones if pb.custom_shape}
for o in shape_objs:
    bpy.data.objects.remove(o)
arm = max((o for o in bpy.data.objects if o.type == "ARMATURE"), key=lambda o: len(o.data.bones))
meshes = [o for o in bpy.data.objects if o.type == "MESH"
          and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
arm.animation_data_clear()
for pb in arm.pose.bones:
    pb.matrix_basis = Matrix()
bpy.context.view_layer.update()

bones = arm.data.bones
Rw = np.array(arm.matrix_world.to_3x3().normalized())          # armature -> world rotation
head = {b.name: np.array(b.head_local) for b in bones}
tail = {b.name: np.array(b.tail_local) for b in bones}
Rrest = {b.name: np.array(b.matrix_local.to_3x3()) for b in bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in bones}
kids = {b.name: [c.name for c in b.children] for b in bones}

# ------------------------------------------------------------------ rig frame
up = Rw.T @ np.array([0, 0, 1.0])                                 # world Z-up in armature space
Vw = np.concatenate([np.array([m.matrix_world @ v.co for v in m.data.vertices]) for m in meshes])
floor_world = Vw[:, 2].min()

# ------------------------------------------------------------------ mapping
ALIASES = {
    "Hips": ["hips", "pelvis", "hip", "root_pelvis", "j_bip_c_hips"],
    "Spine1": ["spine", "spine1", "spine_01", "spine01", "j_bip_c_spine"],
    "Spine2": ["spine2", "spine_02", "spine1_", "j_bip_c_chest"],
    "Chest": ["chest", "spine3", "spine_03", "upperchest", "upper_chest", "spine2_", "j_bip_c_upperchest"],
    "Neck1": ["neck", "neck1", "neck_01", "j_bip_c_neck"],
    "Head": ["head", "j_bip_c_head"],
}
for s, l, short in (("Left", "left", "l"), ("Right", "right", "r")):
    ALIASES.update({
        f"{s}Shoulder": [f"{l}shoulder", f"clavicle_{short}", f"{short}_clavicle", f"{l}_collar", f"{short}collar", f"shoulder_{short}", f"shoulder.{short}"],
        f"{s}Arm": [f"{l}arm", f"{l}upperarm", f"upperarm_{short}", f"{short}_upperarm", f"{l}_shoulder", f"upper_arm.{short}", f"{short}_shoulder"],
        f"{s}ForeArm": [f"{l}forearm", f"{l}lowerarm", f"lowerarm_{short}", f"{short}_elbow", f"{l}_elbow", f"forearm.{short}", f"{short}_forearm"],
        f"{s}Hand": [f"{l}hand", f"hand_{short}", f"{short}_hand", f"{l}_wrist", f"{short}_wrist", f"hand.{short}"],
        f"{s}Leg": [f"{l}upleg", f"{l}upperleg", f"upperleg_{short}", f"{l}thigh", f"thigh_{short}", f"{short}_hip", f"{l}_hip", f"thigh.{short}", f"{short}_thigh"],
        f"{s}Shin": [f"{l}leg", f"{l}lowerleg", f"lowerleg_{short}", f"{l}shin", f"calf_{short}", f"{short}_knee", f"{l}_knee", f"shin.{short}", f"{short}_calf"],
        f"{s}Foot": [f"{l}foot", f"foot_{short}", f"{short}_ankle", f"{l}_ankle", f"foot.{short}", f"{short}_foot"],
        f"{s}ToeBase": [f"{l}toebase", f"{l}toe", f"{l}toes", f"ball_{short}", f"{short}_foot_end", f"toe.{short}", f"{short}_toe"],
    })


def norm(n):
    n = n.lower()
    n = re.sub(r"^(mixamorig\d*[:_]|def[-_]|j_bip_[lrc]_|bip0?1[ _]|armature[|_])", "", n)
    n = re.sub(r"(_\d{2,}|\.\d{3})$", "", n)   # exporter suffixes: upperarm_l_024, Hips.001
    return n.replace(" ", "").replace("-", "_")


def map_by_name():
    m = {}
    lookup = {norm(b.name): b.name for b in bones}
    for soma in BODY:
        cands = [soma.lower()] + ALIASES.get(soma, [])
        for c in cands:
            if c in lookup and lookup[c] not in m.values():
                m[soma] = lookup[c]
                break
    return m


def map_by_topology():
    """For rigs with meaningless names: hips = first bone with >=2 children whose subtrees
    reach far below it; legs = those low subtrees; spine = the highest subtree, until a bone
    whose subtree forks into two lateral branches (arms)."""
    H = max(np.dot(h, up) for h in head.values()) - floor_proj
    hz = {n: float(np.dot(head[n], up)) - floor_proj for n in head}

    def sub(n):
        out = [n]
        for c in kids[n]:
            out += sub(c)
        return out

    lowest = {n: min(hz[s] for s in sub(n)) for n in head}
    highest = {n: max(hz[s] for s in sub(n)) for n in head}
    roots = [n for n in head if parent[n] is None]
    cur = max(roots, key=lambda n: len(sub(n)))
    while True:
        low_kids = [c for c in kids[cur] if lowest[c] < hz[cur] - 0.25 * H]
        if len(low_kids) >= 2 or not kids[cur]:
            break
        cur = max(kids[cur], key=lambda c: len(sub(c)))
    hips = cur
    m = {"Hips": hips}
    legs = sorted([c for c in kids[hips] if lowest[c] < hz[hips] - 0.25 * H], key=lambda c: lowest[c])[:2]
    spine_start = max((c for c in kids[hips] if c not in legs), key=lambda c: highest[c], default=None)
    # left/right from lateral offsets (character left = up x forward; forward unknown yet ->
    # use the hips' rest frame later). Here: sign along the axis separating the two legs.
    lat_axis = head[legs[0]] - head[legs[1]] if len(legs) == 2 else np.array([1.0, 0, 0])
    lat_axis -= np.dot(lat_axis, up) * up
    lat_axis /= np.linalg.norm(lat_axis)

    def chain_down(n):
        out = [n]
        while kids[out[-1]]:
            out.append(min(kids[out[-1]], key=lambda c: lowest[c]))
        return out

    def chain_out(n, sgn):
        out = [n]
        while kids[out[-1]]:
            ks = kids[out[-1]]
            if len(ks) > 2:  # hand with fingers
                break
            out.append(max(ks, key=lambda c: max(sgn * np.dot(head[s], lat_axis) for s in sub(c))))
        return out

    leg_chains = [chain_down(l) for l in legs]
    # spine up to the fork into arms
    spine, cur = [], spine_start
    arms_root = None
    while cur:
        spine.append(cur)
        lateral = [c for c in kids[cur] if max(abs(np.dot(head[s] - head[cur], lat_axis)) for s in sub(c)) > 0.2 * H]
        if len(lateral) >= 2:
            arms_root = cur
            break
        cur = max(kids[cur], key=lambda c: highest[c]) if kids[cur] else None
    if arms_root is None:
        raise SystemExit("topology mapper: no fork into two arms above the hips")
    names = ["Spine1", "Spine2", "Chest"]
    for i, n in enumerate(spine[-3:] if len(spine) >= 3 else spine):
        m[names[-len(spine[-3:]) + i]] = n
    m["Chest"] = arms_root
    neck = max((c for c in kids[arms_root]), key=lambda c: highest[c])
    m["Neck1"] = neck
    m["Head"] = kids[neck][0] if kids[neck] else neck
    arm_roots = [c for c in kids[arms_root] if c != neck]
    # side sign decided after A is known; store both candidates
    return m, leg_chains, arm_roots, chain_out, lat_axis


floor_proj = float(np.dot(Rw.T @ (np.array([0, 0, floor_world]) - np.array(arm.matrix_world.translation)), up))
mapping = map_by_name()
topo = None
if len(mapping) < 14:
    print(f"[retarget] name mapping found {len(mapping)} bones -> topology matcher")
    m, leg_chains, arm_roots, chain_out, lat_axis = map_by_topology()
    topo = (leg_chains, arm_roots, chain_out, lat_axis)
    mapping = m

# forward from the legs: foot -> toe, or knee bend; fallback -Y (glTF +Z forward)
def leg_bone(side):
    return mapping.get(f"{side}Foot")


fwd = None
if topo is None and mapping.get("LeftFoot") and mapping.get("LeftToeBase"):
    f = sum(head[mapping[f"{s}ToeBase"]] - head[mapping[f"{s}Foot"]] for s in ("Left", "Right")
            if mapping.get(f"{s}ToeBase") and mapping.get(f"{s}Foot"))
    fwd = f - np.dot(f, up) * up
if topo is not None:
    leg_chains = topo[0]
    f = np.zeros(3)
    for ch in leg_chains:
        if len(ch) >= 4:
            f += head[ch[3]] - head[ch[2]]
    if np.linalg.norm(f) < 1e-6:
        f = Rw.T @ np.array([0, -1.0, 0])
    fwd = f - np.dot(f, up) * up
if fwd is None or np.linalg.norm(fwd) < 1e-6:
    fwd = Rw.T @ np.array([0, -1.0, 0])
fwd /= np.linalg.norm(fwd)
left = np.cross(up, fwd)
A = np.stack([left, up, fwd], 1)            # columns: SOMA X(left), Y(up), Z(fwd) in rig space

if topo is not None:  # finish topology mapping with sides now that 'left' is known
    leg_chains, arm_roots, chain_out, lat_axis = topo
    for ch in leg_chains:
        side = "Left" if np.dot(head[ch[0]] - head[mapping["Hips"]], left) > 0 else "Right"
        ch = [b for b in ch if np.linalg.norm(head[b] - tail[b]) > 1e-4]
        for soma, b in zip([f"{side}Leg", f"{side}Shin", f"{side}Foot", f"{side}ToeBase"], ch):
            mapping[soma] = b
    for r in arm_roots:
        sgn = 1 if np.dot(head[r] - head[mapping["Chest"]], left) > 0 else -1
        side = "Left" if sgn > 0 else "Right"
        ch = chain_out(r, sgn * float(np.sign(np.dot(lat_axis, left)) or 1))
        names = ["Shoulder", "Arm", "ForeArm", "Hand"] if len(ch) >= 4 else ["Arm", "ForeArm", "Hand"]
        for n, b in zip(names, ch):
            mapping[f"{side}{n}"] = b

print("[retarget] mapping:", json.dumps(mapping))

# ------------------------------------------------------------------ motion
mo = load_motion(MOTION)
G, hips_track, fps = mo["global_rot_mats"], mo["hips"], mo["fps"]
T = len(G)
N = tpose(G, mo["joints0"])                     # SOMA T-pose joint positions
inv_map = {v: k for k, v in mapping.items()}

# rest corrections
Crest = {}
for soma, b in mapping.items():
    tgt = AIM.get(soma)
    if not tgt:
        continue
    src_dir = A @ (N[IDX[tgt]] - N[IDX[soma]])
    nxt = mapping.get(tgt)
    d = (head[nxt] - head[b]) if nxt else (tail[b] - head[b])
    if np.linalg.norm(d) < 1e-6:
        continue
    Crest[b] = rotation_between(d, src_dir)

# hip scaling
src_floor = mo["joints0"][:, 1].min()
src_hip_h = mo["joints0"][0, 1] - src_floor
hips_b = mapping["Hips"]
tgt_hip_h = float(np.dot(head[hips_b], up)) - floor_proj
scale = tgt_hip_h / max(src_hip_h, 1e-6)

order = []  # parents before children
def walk(n):
    order.append(n)
    for c in kids[n]:
        walk(c)
for b in bones:
    if b.parent is None:
        walk(b.name)

sc = bpy.context.scene
sc.render.fps = int(round(fps))
sc.frame_start, sc.frame_end = 1, T
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"

prevq = {}
for t in range(T):
    Wd = {}
    for n in order:
        p = parent[n]
        if n in inv_map:
            j = IDX[inv_map[n]]
            Wd[n] = A @ G[t, j] @ A.T @ Crest.get(n, np.eye(3))
        else:
            Wd[n] = Wd[p] if p else np.eye(3)
        Wp = Wd[p] if p else np.eye(3)
        basis = Rrest[n].T @ Wp.T @ Wd[n] @ Rrest[n]
        q = mat_to_quat(basis)
        if n in prevq and np.dot(q, prevq[n]) < 0:
            q = -q
        prevq[n] = q
        pb = arm.pose.bones[n]
        pb.rotation_quaternion = Quaternion(q)
        pb.keyframe_insert("rotation_quaternion", frame=t + 1)
    # hips translation
    d = A @ (hips_track[t] - hips_track[0]) * scale
    d_h = d - np.dot(d, up) * up
    hz = (hips_track[t, 1] - src_floor) * scale
    target = head[hips_b] - np.dot(head[hips_b], up) * up + d_h + (floor_proj + hz) * up
    p = parent[hips_b]
    loc = Rrest[hips_b].T @ (target - head[hips_b])  # assumes hips' ancestors stay at rest
    pb = arm.pose.bones[hips_b]
    pb.location = loc
    pb.keyframe_insert("location", frame=t + 1)

if arm.animation_data and arm.animation_data.action:
    arm.animation_data.action.name = MOTION.stem
print(f"[retarget] {T} frames @ {fps:g} fps, hip scale {scale:.3f}, {len(mapping)} bones mapped")

OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
for m in meshes:
    m.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True,
                          export_animations=True, export_skins=True, export_force_sampling=True)
print("[retarget] wrote", OUT)

# ------------------------------------------------------------------ preview frames
if PREVIEW:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "TEXTURE"
    for m in meshes:
        m.color = (0.85, 0.55, 0.3, 1)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=40, y_subdivisions=40, size=40,
                                    location=(0, 0, floor_world))
    bpy.context.object.color = (0.25, 0.27, 0.3, 1)
    Hh = tgt_hip_h * 1.9
    tracker = bpy.data.objects.new("trk", None)
    sc.collection.objects.link(tracker)
    c = tracker.constraints.new("COPY_LOCATION")
    c.target, c.subtarget, c.use_z = arm, hips_b, False
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.parent = tracker
    fw = Rw @ fwd
    lw = Rw @ left
    off = 1.9 * Hh * (0.85 * fw + 0.45 * lw)
    cam.location = (off[0], off[1], floor_world + 0.55 * Hh)
    tc = cam.constraints.new("TRACK_TO")
    tc.target, tc.track_axis, tc.up_axis = tracker, "TRACK_NEGATIVE_Z", "UP_Y"
    tracker.location.z = floor_world + 0.5 * Hh
    c.use_offset = False
    tracker.constraints[0].use_z = False
    cam.data.lens = 55
    sc.render.filepath = str(PREVIEW / "f_")
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(animation=True)
