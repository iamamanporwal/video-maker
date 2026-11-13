"""Traffic + street props for the boulevard shots."""
import math, random
import bpy
from common import *  # noqa: F401,F403
from carlib import load_car, tris

PAL = [(0.75, 0.08, 0.08), (0.08, 0.25, 0.7), (0.9, 0.9, 0.92), (0.05, 0.05, 0.06), (0.1, 0.5, 0.25), (0.85, 0.45, 0.05), (0.55, 0.1, 0.55)]


def tint_body(car, rgb):
    mats = []
    for i, m in enumerate(car.data.materials):
        if m and "body" in m.name:
            m = m.copy()
            m.name = f"body_{rgb[0]:.2f}"
            p = m.node_tree.nodes.get("Principled BSDF")
            if p:
                for l in list(m.node_tree.links):
                    if l.to_socket == p.inputs["Base Color"]:
                        m.node_tree.links.remove(l)
                p.inputs["Base Color"].default_value = (*rgb, 1)
                p.inputs["Metallic"].default_value = 0.55
                p.inputs["Roughness"].default_value = 0.28
            car.data.materials[i] = m


def light_boxes(s, lens, front):
    """tiny emissive boxes (shared mesh) for head/tail lights: returns mesh + (x,y,z) offsets."""
    me = bpy.data.meshes.new("lamp")
    vs = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5), (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
    me.from_pydata(vs, [], [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    me.materials.append(emit_mat("head" if front else "tail", (1.0, 0.93, 0.8) if front else (1.0, 0.04, 0.02), 9.0 if front else 7.0))
    return me


def make_traffic(s, rng, lanes, y_range, n, speed_fn, lod=0.06, nf=1, camera_clear=None):
    """lanes: [(x, dir)] dir=+1 (away from camera: tail lights) / -1 (oncoming: head lights). Returns list of dicts."""
    variants = []
    for rgb in PAL[:5]:
        c = load_car(lod, "carsrc")
        tint_body(c, rgb)
        c.location = (0, 0, -50)
        variants.append(c)
    tail, head = light_boxes(s, 0, False), light_boxes(s, 0, True)
    out = []
    for i in range(n):
        x, d = lanes[i % len(lanes)]
        y = rng.uniform(*y_range)
        if camera_clear and abs(x - camera_clear[0]) < 2.2 and 0 < y - camera_clear[1] < 16:
            y += 30
        src = rng.choice(variants)
        o = bpy.data.objects.new("car", src.data)
        link(o, s)
        o.rotation_euler = (0, 0, 0 if d > 0 else math.pi)
        parts = []
        for sx in (-0.68, 0.68):
            lamp = bpy.data.objects.new("lamp", head if d < 0 else tail)
            link(lamp, s)
            lamp.scale = (0.34, 0.06, 0.13)
            parts.append((lamp, sx))
        out.append({"obj": o, "x": x, "d": d, "y0": y, "v": speed_fn(x, d), "lamps": parts})
    return out


def place_traffic(cars, t):
    """t = seconds → set transforms (called per frame; keyed by caller)."""
    for c in cars:
        y = c["y0"] + c["d"] * c["v"] * t
        c["obj"].location = (c["x"], y, 0.0)
        for lamp, sx in c["lamps"]:
            lamp.location = (c["x"] + sx, y - 2.1, 0.62)


def key_traffic(cars, nf, fps=30):
    for f in range(1, nf + 1):
        t = (f - 1) / fps
        place_traffic(cars, t)
        for c in cars:
            c["obj"].keyframe_insert("location", frame=f)
            for lamp, _ in c["lamps"]:
                lamp.keyframe_insert("location", frame=f)
