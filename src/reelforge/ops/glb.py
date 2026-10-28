"""GLB inspection without three.js: bounds with node transforms baked, materials/textures, texture check, anchors.

Normalisation in the renderer is a rigid transform (bake node transform, centre, uniform scale to length 1),
never a geometry edit.
"""

from __future__ import annotations

import io
import json
import struct
from pathlib import Path
from typing import Optional

import numpy as np

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path: Path) -> tuple[dict, bytes]:
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError(f"{path} is not a GLB")
    off, gltf, bin_ = 12, None, b""
    while off < length:
        clen, ctype = struct.unpack_from("<I4s", data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == b"JSON":
            gltf = json.loads(chunk)
        elif ctype == b"BIN\x00":
            bin_ = chunk
        off += 8 + clen
    return gltf, bin_


def _quat_mat(q) -> np.ndarray:
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _local(node: dict) -> np.ndarray:
    if "matrix" in node:
        return np.array(node["matrix"], dtype=float).reshape(4, 4).T
    m = np.eye(4)
    s = np.diag(node.get("scale", [1, 1, 1]))
    r = _quat_mat(node.get("rotation", [0, 0, 0, 1]))
    m[:3, :3] = r @ s
    m[:3, 3] = node.get("translation", [0, 0, 0])
    return m


def _accessor(gltf: dict, bin_: bytes, idx: int) -> np.ndarray:
    acc = gltf["accessors"][idx]
    bv = gltf["bufferViews"][acc["bufferView"]]
    dt = np.dtype(COMP[acc["componentType"]])
    n = NCOMP[acc["type"]]
    start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride") or dt.itemsize * n
    count = acc["count"]
    if stride == dt.itemsize * n:
        arr = np.frombuffer(bin_, dtype=dt, count=count * n, offset=start).reshape(count, n)
    else:
        rows = [np.frombuffer(bin_, dtype=dt, count=n, offset=start + i * stride) for i in range(count)]
        arr = np.stack(rows)
    return arr.astype(np.float64)


def world_positions(gltf: dict, bin_: bytes, max_points: int = 400_000) -> np.ndarray:
    pts = []
    scene = gltf.get("scenes", [{}])[gltf.get("scene", 0)] if gltf.get("scenes") else {"nodes": list(range(len(gltf.get("nodes", []))))}

    def walk(ni: int, parent: np.ndarray):
        node = gltf["nodes"][ni]
        m = parent @ _local(node)
        if "mesh" in node:
            for prim in gltf["meshes"][node["mesh"]]["primitives"]:
                if "POSITION" in prim["attributes"]:
                    v = _accessor(gltf, bin_, prim["attributes"]["POSITION"])
                    if len(v) > max_points:
                        v = v[:: len(v) // max_points + 1]
                    pts.append(v @ m[:3, :3].T + m[:3, 3])
        for c in node.get("children", []):
            walk(c, m)

    for ni in scene.get("nodes", []):
        walk(ni, np.eye(4))
    return np.concatenate(pts) if pts else np.zeros((0, 3))


def inspect_glb(path: Path) -> dict:
    gltf, bin_ = read_glb(path)
    P = world_positions(gltf, bin_)
    lo, hi = P.min(axis=0), P.max(axis=0)
    ext = hi - lo
    up_guess = "z" if ext[2] < ext[1] * 0.8 and ext[2] < ext[0] else "y"
    mats = []
    for m in gltf.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        mats.append({"name": m.get("name"), "baseColorFactor": pbr.get("baseColorFactor"),
                     "has_baseColorTexture": "baseColorTexture" in pbr,
                     "metallic": pbr.get("metallicFactor"), "roughness": pbr.get("roughnessFactor"),
                     "emissive": m.get("emissiveFactor")})
    root_rot = [n.get("rotation") or n.get("matrix") for n in gltf.get("nodes", [])[:3]]
    return {
        "file": str(path), "size_mb": round(Path(path).stat().st_size / 1e6, 2),
        "generator": gltf.get("asset", {}).get("generator"),
        "meshes": len(gltf.get("meshes", [])), "nodes": len(gltf.get("nodes", [])),
        "vertices_sampled": int(len(P)),
        "bounds": {"min": lo.round(4).tolist(), "max": hi.round(4).tolist(), "extent": ext.round(4).tolist()},
        "center": ((lo + hi) / 2).round(4).tolist(),
        "normalise_scale": round(float(1 / max(ext.max(), 1e-9)), 6),
        "up_axis_guess": up_guess, "root_transforms": root_rot,
        "materials": mats, "textures": len(gltf.get("textures", [])), "images": len(gltf.get("images", [])),
    }


def base_color_image(path: Path):
    from PIL import Image

    gltf, bin_ = read_glb(path)
    for m in gltf.get("materials", []):
        t = m.get("pbrMetallicRoughness", {}).get("baseColorTexture")
        if t is None:
            continue
        img = gltf["images"][gltf["textures"][t["index"]]["source"]]
        if "bufferView" not in img:
            continue
        bv = gltf["bufferViews"][img["bufferView"]]
        raw = bin_[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
        return Image.open(io.BytesIO(raw)).convert("RGB")
    return None


def texture_check(glb: Path, source_image: Optional[Path] = None, out_png: Optional[Path] = None) -> dict:
    """Is the paint baked lighter than the source image? If so, allow a base-colour factor only (logged)."""
    from PIL import Image

    tex = base_color_image(glb)
    if tex is None:
        return {"has_texture": False}
    if out_png:
        out_png.parent.mkdir(parents=True, exist_ok=True)
        tex.save(out_png)
    a = np.asarray(tex.resize((256, 256)), dtype=float)
    # Ignore near-white and near-black padding in the atlas.
    mask = (a.mean(axis=2) > 8) & (a.mean(axis=2) < 248)
    tex_l = float(a[mask].mean()) if mask.any() else float(a.mean())
    res = {"has_texture": True, "texture_mean_luma": round(tex_l, 2)}
    if source_image and Path(source_image).exists():
        s = np.asarray(Image.open(source_image).convert("RGB").resize((256, 256)), dtype=float)
        src_l = float(s.mean())
        ratio = src_l / max(tex_l, 1e-6)
        res.update(source_mean_luma=round(src_l, 2), ratio=round(ratio, 3))
        if ratio < 0.9:
            f = round(max(0.5, ratio), 3)
            res["recommend"] = {"baseColorFactor": [f, f, f, 1.0],
                                "note": "texture baked lighter than source; base-colour factor only (no texture edit)"}
    return res


def anchors(glb: Path, up: str = "auto", k_frac: float = 0.02) -> dict:
    """Thruster/wheel anchors = centroids of the lowest vertices in each quadrant, in normalised space."""
    gltf, bin_ = read_glb(glb)
    P = world_positions(gltf, bin_)
    info = inspect_glb(glb)
    if up == "auto":
        up = info["up_axis_guess"]
    ui = {"x": 0, "y": 1, "z": 2}[up]
    P = (P - np.array(info["center"])) * info["normalise_scale"]
    plane = [i for i in range(3) if i != ui]
    # Length axis = longer of the two plane axes.
    ext = P.max(axis=0) - P.min(axis=0)
    la, wa = sorted(plane, key=lambda i: -ext[i])
    out = {}
    for name, sl, sw in (("front_left", 1, -1), ("front_right", 1, 1), ("rear_left", -1, -1), ("rear_right", -1, 1)):
        q = P[(np.sign(P[:, la]) == sl) & (np.sign(P[:, wa]) == sw)]
        if not len(q):
            continue
        k = max(10, int(len(q) * k_frac))
        low = q[np.argsort(q[:, ui])[:k]]
        out[name] = low.mean(axis=0).round(4).tolist()
    return {"up": up, "length_axis": "xyz"[la], "width_axis": "xyz"[wa], "anchors": out}
