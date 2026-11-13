"""Procedural dusk city for the gta6-optimized shots (Blender 5.x). Streets on a grid; boulevard = x=0 running +Y.

    c = City(s, nx, ny, seed)   → c.bld (list of dict: obj, cx, cy, w, d, h, tiers[]), c.road, c.stripes
"""
import math, random
import bpy
from mathutils import Vector
from common import *  # noqa: F401,F403

PITCH = 56.0                 # street-to-street distance
ROADW = 14.0                 # street width
LOT = (PITCH - ROADW) / 2    # lot size (2x2 lots per block)


def sky(s, top=(0.012, 0.025, 0.09), mid=(0.50, 0.14, 0.20), hor=(1.0, 0.40, 0.12), strength=1.0):
    w = bpy.data.worlds.new("sky")
    w.use_nodes = True
    s.world = w
    w.node_tree.nodes.clear()
    nt = NT(w.node_tree)
    out = nt.n("ShaderNodeOutputWorld")
    bg = nt.n("ShaderNodeBackground")
    geo = nt.n("ShaderNodeNewGeometry")
    sz = nt.n("ShaderNodeSeparateXYZ", ins={"Vector": geo.outputs["Incoming"]})
    el = nt.math("MULTIPLY", sz.outputs["Z"], -1.0)          # elevation of the ray: -1..1
    a = nt.maprange(el, 0.0, 0.2, 0.0, 1.0, smooth=True)
    b = nt.maprange(el, 0.15, 0.85, 0.0, 1.0, smooth=True)
    c1 = nt.mix(a, hor + (1,), mid + (1,))
    c2 = nt.mix(b, c1, top + (1,))
    below = nt.maprange(el, -0.04, 0.0, 0.0, 1.0)
    col = nt.mix(below, (0.02, 0.02, 0.03, 1), c2)
    nt.set(bg.inputs[0], col)
    bg.inputs[1].default_value = strength
    nt.t.links.new(bg.outputs[0], out.inputs[0])
    return w


def facade_mat():
    m, nt, out = new_mat("facade")
    geo = nt.n("ShaderNodeNewGeometry")
    oi = nt.n("ShaderNodeObjectInfo")
    nsep = nt.n("ShaderNodeSeparateXYZ", ins={"Vector": geo.outputs["Normal"]})
    psep = nt.n("ShaderNodeSeparateXYZ", ins={"Vector": geo.outputs["Position"]})
    side = nt.math("LESS_THAN", nt.math("ABSOLUTE", nsep.outputs["Z"]), 0.5)
    h = nt.math("ADD", nt.math("MULTIPLY", psep.outputs["X"], nt.math("ABSOLUTE", nsep.outputs["Y"])),
                nt.math("MULTIPLY", psep.outputs["Y"], nt.math("ABSOLUTE", nsep.outputs["X"])))
    gx, gz = nt.math("DIVIDE", h, 2.4), nt.math("DIVIDE", psep.outputs["Z"], 3.3)
    fx, fz = nt.math("FRACT", gx), nt.math("FRACT", gz)
    win = nt.math("MULTIPLY", nt.math("MULTIPLY", nt.math("GREATER_THAN", fx, 0.16), nt.math("LESS_THAN", fx, 0.84)),
                  nt.math("MULTIPLY", nt.math("GREATER_THAN", fz, 0.2), nt.math("LESS_THAN", fz, 0.78)))
    win = nt.math("MULTIPLY", win, nt.math("GREATER_THAN", psep.outputs["Z"], 3.0))
    win = nt.math("MULTIPLY", win, side)
    cell = nt.n("ShaderNodeCombineXYZ", ins={"X": nt.math("FLOOR", gx), "Y": nt.math("FLOOR", gz),
                                             "Z": nt.math("ADD", nt.math("MULTIPLY", oi.outputs["Random"], 97.0), nt.math("MULTIPLY", nt.math("ABSOLUTE", nsep.outputs["X"]), 13.0))})
    wn = nt.n("ShaderNodeTexWhiteNoise", noise_dimensions="3D", ins={"Vector": cell.outputs[0]})
    r = wn.outputs["Value"]
    shifted = nt.vmath("ADD", cell.outputs[0], (7.1, 3.3, 1.9))
    wn2 = nt.n("ShaderNodeTexWhiteNoise", noise_dimensions="3D", ins={"Vector": shifted.outputs[0]})
    r2 = wn2.outputs["Value"]
    lit = nt.math("GREATER_THAN", r, 0.42)
    lcol = nt.mix(nt.math("GREATER_THAN", r2, 0.62), (1.0, 0.72, 0.38, 1),
                  nt.mix(nt.math("GREATER_THAN", r2, 0.88), (0.65, 0.82, 1.0, 1), (1.0, 0.22, 0.55, 1)))
    ramp = nt.n("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    cols = [(0.62, 0.30, 0.28, 1), (0.66, 0.58, 0.46, 1), (0.12, 0.34, 0.36, 1), (0.40, 0.30, 0.50, 1), (0.30, 0.30, 0.33, 1), (0.55, 0.42, 0.30, 1)]
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, cols[0]
    els[1].position, els[1].color = 1 / 6, cols[1]
    for i in range(2, 6):
        e = ramp.color_ramp.elements.new(i / 6.0)
        e.color = cols[i]
    nt.t.links.new(oi.outputs["Random"], ramp.inputs["Fac"])
    dark = nt.vmath("SCALE", ramp.outputs["Color"], scale=0.3)
    wall = nt.mix(nt.maprange(psep.outputs["Z"], 0.0, 8.0, 0.0, 1.0), dark.outputs[0], ramp.outputs["Color"])
    roof = nt.math("GREATER_THAN", nsep.outputs["Z"], 0.5)
    base = nt.mix(win, wall, (0.012, 0.02, 0.04, 1))
    base = nt.mix(roof, base, (0.03, 0.03, 0.035, 1))
    p = nt.n("ShaderNodeBsdfPrincipled", ins={"Metallic": 0.0})
    nt.set(p.inputs["Base Color"], base)
    nt.set(p.inputs["Roughness"], nt.math("ADD", nt.math("MULTIPLY", win, -0.7), 0.8))
    nt.set(p.inputs["Emission Color"], lcol)
    nt.set(p.inputs["Emission Strength"], nt.math("MULTIPLY", nt.math("MULTIPLY", win, lit), 3.2))
    nt.t.links.new(p.outputs[0], out.inputs[0])
    return m


class City:
    def __init__(self, s, nx=9, ny=9, seed=3, y0=-PITCH):
        self.s, self.rng = s, random.Random(seed)
        self.bld = []
        self.fm = facade_mat()
        me = bpy.data.meshes.new("unit")           # unit cube, origin at base centre (z 0..1)
        vs = [(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0), (-.5, -.5, 1), (.5, -.5, 1), (.5, .5, 1), (-.5, .5, 1)]
        fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        me.from_pydata(vs, [], fs)
        me.update()
        me.materials.append(self.fm)
        self.unit = me
        self.nx, self.ny = nx, ny
        self.x0 = -(nx // 2) * PITCH                      # street i sits at x0 + i*PITCH; i = nx//2 is the boulevard x=0
        self.y0 = y0
        self._lots()
        self._ground()
        self._lines()

    def block_origin(self, i, j):
        return self.x0 + i * PITCH + ROADW / 2, self.y0 + j * PITCH + ROADW / 2

    def add_building(self, cx, cy, w, d, h, tier=True):
        o = bpy.data.objects.new("b", self.unit)
        o.location, o.scale = (cx, cy, 0.0), (w, d, h)
        link(o, self.s)
        rec = {"obj": o, "cx": cx, "cy": cy, "w": w, "d": d, "h": h, "tiers": []}
        if tier and h > 22 and self.rng.random() < 0.6:
            o2 = bpy.data.objects.new("t", self.unit)
            o2.location, o2.scale = (cx, cy, h), (w * 0.62, d * 0.62, h * self.rng.uniform(0.22, 0.4))
            link(o2, self.s)
            rec["tiers"].append(o2)
        self.bld.append(rec)
        return rec

    def _lots(self):
        r = self.rng
        for i in range(self.nx):
            for j in range(self.ny):
                bx, by = self.block_origin(i, j)
                dcx, dcy = (i - self.nx / 2) / (self.nx / 2), (j - self.ny / 2) / (self.ny / 2)
                core = max(0.15, 1.0 - 0.55 * math.hypot(dcx, dcy))
                for a in (0, 1):
                    for b in (0, 1):
                        w, d = LOT - r.uniform(1.5, 4.5), LOT - r.uniform(1.5, 4.5)
                        h = r.uniform(10, 34) + core * r.uniform(0, 62) * (1 if r.random() < 0.8 else 0.2)
                        self.add_building(bx + a * LOT + LOT / 2, by + b * LOT + LOT / 2, w, d, h)

    def _ground(self):
        W, Dp = self.nx * PITCH + 400, self.ny * PITCH + 400
        cx, cy = self.x0 + self.nx * PITCH / 2, self.y0 + self.ny * PITCH / 2
        rm, nt, out = new_mat("asphalt")
        tc = nt.n("ShaderNodeTexCoord")
        nz = nt.n("ShaderNodeTexNoise", noise_dimensions="3D", ins={"Vector": tc.outputs["Object"], "Scale": 0.7, "Detail": 6.0})
        p = nt.n("ShaderNodeBsdfPrincipled", ins={"Metallic": 0.0, "Base Color": (0.035, 0.035, 0.04, 1)})
        nt.set(p.inputs["Roughness"], nt.maprange(nz.outputs["Fac"], 0.3, 0.7, 0.10, 0.34))
        nt.t.links.new(p.outputs[0], out.inputs[0])
        self.road = box("ground", (W, Dp, 0.2), (cx, cy, -0.1), rm)
        sw = pbr("sidewalk", (0.20, 0.19, 0.19), rough=0.6)
        for i in range(self.nx):
            for j in range(self.ny):
                bx, by = self.block_origin(i, j)
                box("curb", (PITCH - ROADW, PITCH - ROADW, 0.3), (bx + LOT, by + LOT, 0.0), sw)

    def _lines(self):
        yl = pbr("ln", (0.9, 0.78, 0.25), rough=0.5, emit=(1.0, 0.78, 0.25), emit_strength=0.6)
        wl = pbr("lw", (0.85, 0.85, 0.85), rough=0.5, emit=(0.9, 0.9, 0.9), emit_strength=0.3)
        meshes = []
        for mat in (wl, yl):
            me = bpy.data.meshes.new("q")
            me.from_pydata([(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)], [], [(0, 1, 2, 3)])
            me.materials.append(mat)
            meshes.append(me)
        Y0, Y1 = self.y0, self.y0 + self.ny * PITCH
        X0, X1 = self.x0, self.x0 + self.nx * PITCH

        def strip(me, x, y, sx, sy):
            o = bpy.data.objects.new("s", me)
            o.location, o.scale = (x, y, 0.012), (sx, sy, 1)
            link(o, self.s)

        for i in range(self.nx + 1):
            x = self.x0 + i * PITCH
            for k in (-0.22, 0.22):
                strip(meshes[1], x + k, (Y0 + Y1) / 2, 0.12, Y1 - Y0)
            for k in (-3.5, 3.5):
                y = Y0
                while y < Y1:
                    strip(meshes[0], x + k, y + 1.5, 0.14, 3.0)
                    y += 9.0
        for j in range(self.ny + 1):
            y = self.y0 + j * PITCH
            for k in (-0.22, 0.22):
                strip(meshes[1], (X0 + X1) / 2, y + k, X1 - X0, 0.12)
