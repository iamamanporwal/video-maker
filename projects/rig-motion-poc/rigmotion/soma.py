"""SOMA-77 skeleton (the skeleton NVIDIA Kimodo writes) + small rotation helpers.

Motion interchange format used by the whole pipeline (``motion.npz``):

    global_rot_mats  [T, 77, 3, 3]  world rotation of each joint *relative to SOMA's T-pose*
    joints0          [77, 3]        posed joint positions on frame 0 (metres)
    hips             [T, 3]         hips (root) position track
    fps              ()             frames per second

Frame: SOMA world axes are X = character's left, Y = up, Z = forward (verified on real
Kimodo clips: walking moves +Z, LeftArm has +X).  Kimodo's own NPZ (`global_rot_mats`,
`posed_joints`) converts to this losslessly, and SMPL/HumanML3D-style backends can be
converted by filling the 22 body joints and leaving fingers at identity.
"""

from __future__ import annotations

import numpy as np

SOMA77 = [
    "Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "HeadEnd", "Jaw",
    "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "LeftHandThumb1", "LeftHandThumb2", "LeftHandThumb3", "LeftHandThumbEnd",
    "LeftHandIndex1", "LeftHandIndex2", "LeftHandIndex3", "LeftHandIndex4", "LeftHandIndexEnd",
    "LeftHandMiddle1", "LeftHandMiddle2", "LeftHandMiddle3", "LeftHandMiddle4", "LeftHandMiddleEnd",
    "LeftHandRing1", "LeftHandRing2", "LeftHandRing3", "LeftHandRing4", "LeftHandRingEnd",
    "LeftHandPinky1", "LeftHandPinky2", "LeftHandPinky3", "LeftHandPinky4", "LeftHandPinkyEnd",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "RightHandThumb1", "RightHandThumb2", "RightHandThumb3", "RightHandThumbEnd",
    "RightHandIndex1", "RightHandIndex2", "RightHandIndex3", "RightHandIndex4", "RightHandIndexEnd",
    "RightHandMiddle1", "RightHandMiddle2", "RightHandMiddle3", "RightHandMiddle4", "RightHandMiddleEnd",
    "RightHandRing1", "RightHandRing2", "RightHandRing3", "RightHandRing4", "RightHandRingEnd",
    "RightHandPinky1", "RightHandPinky2", "RightHandPinky3", "RightHandPinky4", "RightHandPinkyEnd",
    "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "LeftToeEnd",
    "RightLeg", "RightShin", "RightFoot", "RightToeBase", "RightToeEnd",
]
SOMA77_PARENTS = [
    -1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 6, 3, 11, 12, 13, 14, 15, 16, 17, 14, 19, 20, 21, 22, 14, 24, 25, 26,
    27, 14, 29, 30, 31, 32, 14, 34, 35, 36, 37, 3, 39, 40, 41, 42, 43, 44, 45, 42, 47, 48, 49, 50, 42,
    52, 53, 54, 55, 42, 57, 58, 59, 60, 42, 62, 63, 64, 65, 0, 67, 68, 69, 70, 0, 72, 73, 74, 75,
]
IDX = {n: i for i, n in enumerate(SOMA77)}

# Body joints the retargeter drives, and for limb bones the joint their bone points at
# (used to straighten an A-pose / odd rest pose into SOMA's T-pose before applying motion).
BODY = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Head"] + [
    f"{s}{j}" for s in ("Left", "Right")
    for j in ("Shoulder", "Arm", "ForeArm", "Hand", "Leg", "Shin", "Foot", "ToeBase")
]
AIM = {}
for _s in ("Left", "Right"):
    AIM.update({
        f"{_s}Shoulder": f"{_s}Arm", f"{_s}Arm": f"{_s}ForeArm", f"{_s}ForeArm": f"{_s}Hand",
        f"{_s}Hand": f"{_s}HandMiddle1", f"{_s}Leg": f"{_s}Shin", f"{_s}Shin": f"{_s}Foot",
        f"{_s}Foot": f"{_s}ToeBase", f"{_s}ToeBase": f"{_s}ToeEnd",
    })


def quat_to_mat(q: np.ndarray) -> np.ndarray:
    """[..., 4] (w, x, y, z) -> [..., 3, 3]."""
    q = np.asarray(q, dtype=np.float64)
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = (q[..., i] for i in range(4))
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
        np.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
        np.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1),
    ], -2)


def mat_to_quat(m: np.ndarray) -> np.ndarray:
    """[..., 3, 3] -> [..., 4] (w, x, y, z), sign-normalised so w >= 0."""
    m = np.asarray(m, dtype=np.float64)
    w = np.sqrt(np.clip(1 + m[..., 0, 0] + m[..., 1, 1] + m[..., 2, 2], 0, None)) / 2
    x = np.sqrt(np.clip(1 + m[..., 0, 0] - m[..., 1, 1] - m[..., 2, 2], 0, None)) / 2
    y = np.sqrt(np.clip(1 - m[..., 0, 0] + m[..., 1, 1] - m[..., 2, 2], 0, None)) / 2
    z = np.sqrt(np.clip(1 - m[..., 0, 0] - m[..., 1, 1] + m[..., 2, 2], 0, None)) / 2
    x = np.copysign(x, m[..., 2, 1] - m[..., 1, 2])
    y = np.copysign(y, m[..., 0, 2] - m[..., 2, 0])
    z = np.copysign(z, m[..., 1, 0] - m[..., 0, 1])
    q = np.stack([w, x, y, z], -1)
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def axis_angle(axis: np.ndarray, angle: float) -> np.ndarray:
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * (k @ k)


def rotation_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Smallest rotation taking direction a onto direction b."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if c < -0.999999:  # opposite: any perpendicular axis
        p = np.cross(a, [1.0, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1.0, 0])
        return axis_angle(p, np.pi)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def slerp_mats(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    """Slerp between two stacks of rotation matrices [..., 3, 3]."""
    qa, qb = mat_to_quat(a), mat_to_quat(b)
    d = np.sum(qa * qb, -1, keepdims=True)
    qb = np.where(d < 0, -qb, qb)
    d = np.abs(d).clip(-1, 1)
    th = np.arccos(d)
    s = np.sin(th)
    small = s < 1e-6
    wa = np.where(small, 1 - t, np.sin((1 - t) * th) / np.where(small, 1, s))
    wb = np.where(small, t, np.sin(t * th) / np.where(small, 1, s))
    return quat_to_mat(wa * qa + wb * qb)


def tpose(global_rots: np.ndarray, joints0: np.ndarray) -> np.ndarray:
    """SOMA T-pose joint positions (hips at origin) recovered from frame 0.

    Kimodo poses joints as x_j = x_p + G_p (N_j - N_p), so N_j - N_p = G_p^T (x_j - x_p).
    """
    n = np.zeros((77, 3))
    for j, p in enumerate(SOMA77_PARENTS):
        if p >= 0:
            n[j] = n[p] + global_rots[0, p].T @ (joints0[j] - joints0[p])
    return n


def load_motion(path) -> dict:
    """Read a Kimodo NPZ (global_rot_mats/posed_joints) or the packed form (quats/joints0/hips)."""
    d = np.load(path, allow_pickle=False)
    if "global_rot_mats" in d.files and "posed_joints" in d.files:
        g, x = d["global_rot_mats"], d["posed_joints"]
        if g.ndim == 5:  # [samples, T, J, 3, 3]
            g, x = g[0], x[0]
        fps = float(d["fps"]) if "fps" in d.files else 30.0
        return {"global_rot_mats": g.astype(np.float64), "joints0": x[0].astype(np.float64),
                "hips": x[:, 0].astype(np.float64), "fps": fps}
    if "quats" in d.files:
        return {"global_rot_mats": quat_to_mat(d["quats"]), "joints0": d["joints0"].astype(np.float64),
                "hips": d["hips"].astype(np.float64), "fps": float(d["fps"])}
    if "joints0" in d.files and "global_rot_mats" in d.files:  # our own format
        return {k: d[k].astype(np.float64) if k != "fps" else float(d[k]) for k in
                ("global_rot_mats", "joints0", "hips", "fps")}
    raise ValueError(f"{path}: unrecognised motion NPZ keys {d.files}")


def save_motion(path, m: dict) -> None:
    np.savez_compressed(path, global_rot_mats=m["global_rot_mats"].astype(np.float32),
                        joints0=m["joints0"].astype(np.float32), hips=m["hips"].astype(np.float32),
                        fps=np.float32(m["fps"]))
