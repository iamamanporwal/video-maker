"""python3 film.py → studio/timeline.json : the animated shot list for the in-Studio film, timed on the VO word clock.
Actors: humanoids {pos, look, anim|to+speed, face, layer}; props {cf:[x,y,z,yaw,pitch,roll] (bottom-centre), to, dur, scale,
scale1, bob, wobble, spin, delay, ease}; Cube {cf, size, size1, face, ghost}; Robot (client) [{cf, to, h, h1, dur, bob}].
Camera {p0,l0,p1,l1,fov,fov1,roll,roll1,snap,track,trackOff,shake,ease}."""
import json
from pathlib import Path

D = Path(__file__).resolve().parent
M = json.loads((D / "out/words.json").read_text())
L = {l["id"]: l for l in M["lines"]}


def W(lid, i=0):
    return L[lid]["words"][i][1]


def cam(p0, l0, p1=None, l1=None, fov=62, **kw):
    c = {"p0": p0, "l0": l0, "fov": fov}
    if p1: c["p1"] = p1
    if l1: c["l1"] = l1
    c.update(kw)
    return c


H = lambda pos, look=None, anim="idle", face="happy", **kw: dict(pos=pos, look=look, anim=anim, face=face, **kw)
TOWN_LOOK = [4, 0, -33]
TOWNFOLK_SHOCK = {
    "Hero": H([4, 0, -33], [4, 0, -10], "idle", "nervous"),
    "Lady": H([-3.5, 0.6, -18], TOWN_LOOK, "scared", "shocked"),
    "Dude": H([0.5, 0.6, -17], TOWN_LOOK, "idle", "shocked"),
    "Neighbor": H([7.5, 0.6, -17.5], TOWN_LOOK, "scared", "shocked"),
    "Mayor": H([11.5, 0.6, -18.5], TOWN_LOOK, "idle", "angry"),
    "Donut": {"cf": [14.8, 0.6, -17.5, 200], "scale": 1.0},
}
GIANT = {"cf": [4, 0, -8, 0], "size": 26, "face": "angry"}
DESK_NIGHT = {"Table": {"cf": [4, 0, -31.6]}, "Laptop": {"cf": [4, 3.33, -31.4, 180], "scale": 1.15}}

SHOTS = [
    # --- hook: the flesh donut chases the neighbour
    dict(id="S01", t=0.0, light="day", actors={
        "Neighbor": H([-96, 0.6, -19], [-70, 0, -19], face="scream", to=[-76, 0.6, -19], speed=15),
        "Donut": {"cf": [-102, 0.6, -19, -120], "to": [-84, 0.6, -19, -120], "dur": 2.9, "bob": 0.9, "scale": 1.25, "ease": "linear"}},
         cam=cam([-95, 2.4, -7], [-95, 2.6, -19], [-85, 2.6, -8], fov=68, track="Donut", trackOff=[2.2, 0.6, 0], snap=True, roll=5, ease="linear")),
    dict(id="S02", t=W("h2"), actors={
        "Lady": H([98, 0.6, -17], [98, 0, 0], "hold", "nervous"),
        "Dude": H([102.5, 0.6, -18], [99, 0, -10], "scared", "shocked"),
        "Laptop": {"cf": [98, 2.95, -15.5, 0], "scale": 1.0}},
         cam=cam([99.5, 4.0, -4], [99.5, 3.6, -16], [99.5, 3.9, -8], roll=-5)),
    dict(id="S03", t=W("a1"), screen="donut", actors={
        "Neighbor": H([-91, 0.6, -14.2], [-91, 0, -30], "typing", "grin"),
        "Table": {"cf": [-91, 0.6, -16.4]}, "Laptop": {"cf": [-91, 3.93, -16.6, 0], "scale": 1.7}},
         cam=cam([-87.4, 7.0, -9.0], [-91, 4.3, -17.4], [-88.6, 6.3, -12.6], [-91, 4.3, -17.5])),
    dict(id="S04", t=W("a2"), actors={
        "Neighbor": H([-84.6, 0, -24.5], [-87, 0, -8], "shrug", "cry"),
        "Donut": {"cf": [-89.5, 0, -24, 165], "to": [-88.2, 0, -23, 195], "dur": 3.0, "bob": 0.7, "scale": 1.35}},
         cam=cam([-86.4, 4.2, -9], [-86.4, 4.4, -26], [-86.4, 4.2, -12])),
    dict(id="S04b", t=W("a2", 10), actors={
        "Neighbor": H([-84.6, 0, -24.5], [-87, 0, -8], "shrug", "cry"),
        "Donut": {"cf": [-88.2, 0, -23, 180], "dur": 1, "bob": 0.5, "scale": 1.35}},
         cam=cam([-88.2, 3.0, -16], [-88.2, 2.6, -23], [-88.2, 2.9, -17.5], snap=True, shake=0.3, roll=-6)),
    dict(id="S05", t=W("a3"), actors={
        "Mayor": H([110, 0.6, -15.5], [110, 0, 0], "flex", "grin"),
        "Abs": {"cf": [110, 2.55, -14.75, 180], "scale": 0.62, "bob": 0.08}},
         cam=cam([110, 3.6, -4], [110, 4.4, -16], [110, 4.0, -8.5], roll=4)),
    dict(id="S06", t=W("a3", 6), light="night", actors={
        "Abs": {"cf": [117, 0.6, -19, -90], "to": [127, 0.6, -19, -90], "dur": 2.0, "bob": 0.3, "wobble": 7, "scale": 1.0, "ease": "linear"}},
         cam=cam([113, 1.6, -13.5], [118, 1.4, -19], [116, 1.7, -14], fov=48, track="Abs", trackOff=[0, 0.4, 0])),
    # --- and me?
    dict(id="S07", t=W("m1"), light="day", actors={
        "Hero": H([4, 0, -37], [4, 0, -10], face="grin", to=[4, 0, -27.5], speed=6, after="hips")},
         cam=cam([4, 4.2, -15], [4, 4.4, -30], [4, 4.2, -19], fov=45, track="Hero", trackOff=[0, -0.8, 0])),
    dict(id="S08", t=W("m2"), screen="cube", actors={
        "Hero": H([4, 0, -28.2], [4, 0, -45], "typing", "grin"),
        "Table": {"cf": [4, 0, -30.4]}, "Laptop": {"cf": [4, 3.33, -30.9, 0], "scale": 1.7}},
         cam=cam([6.8, 6.6, -23.4], [4, 4.0, -31.4], [6.0, 6.0, -25.2], [4, 4.0, -31.5])),
    dict(id="S09a", t=W("c1"), actors={
        "Hero": H([1.8, 0, -30.5], [6, 0, -24], "idle", "happy"),
        "Cube": {"cf": [5.6, 0, -29.2, 25], "size": 0.05, "size1": 2, "dur": 0.45, "delay": 0.3}},
         cam=cam([6.2, 3.6, -19.8], [3.6, 2.6, -30], [5.2, 3.3, -22], roll=-4)),
    dict(id="S09b", t=W("c1", 10), actors={
        "Hero": H([1.8, 0, -30.5], [6, 0, -27.5], "pointAt", "grin"),
        "Cube": {"cf": [5.6, 0, -29.2, 25], "size": 2}},
         cam=cam([3.9, 4.6, -25.2], [2.3, 4.4, -30.3], [3.5, 4.6, -26.8], snap=True)),
    dict(id="S10a", t=W("c2"), actors={
        "Hero": H([1.8, 0, -30.5], [6, 0, -27.5], "pointAt", "grin"),
        "Cube": {"cf": [5.6, 0, -29.2, 25], "size": 2}},
         events=[{"at": 0.42, "actor": "Cube", "prop": {"cf": [5.6, 0, -29.2, 25], "size": 2, "ghost": True}}],
         cam=cam([5.6, 2.6, -23.2], [5.5, 1.2, -29.2], [5.6, 2.4, -24], fov=42, snap=True)),
    dict(id="S10b", t=L["c2"]["end"] + 0.2, actors={
        "Hero": H([1.8, 0, -30.5], [6, 0, -24], "hips", "grin"),
        "Cube": {"cf": [5.6, 0, -29.2, 25], "size": 2, "ghost": True}},
         cam=cam([5.2, 3.3, -21.6], [3.6, 2.8, -30], [5.0, 3.2, -23], roll=5)),
    dict(id="S11", t=W("c3"), actors=TOWNFOLK_SHOCK,
         cam=cam([3, 6.5, -42.5], [5.5, 3, -18], [3.4, 5.6, -38.5], fov=68, ease="linear")),
    dict(id="S12a", t=W("c4"), actors=TOWNFOLK_SHOCK,
         cam=cam([10.3, 5.4, -22.4], [11.5, 5.0, -18.5], [10.6, 5.3, -21.8], snap=True, roll=-6)),
    dict(id="S12b", t=W("c4", 2), actors=TOWNFOLK_SHOCK,
         cam=cam([-2.9, 4.9, -23.4], [-3.5, 4.5, -18], [-3.0, 4.8, -22.6], snap=True, roll=6)),
    dict(id="S12c", t=W("c4", 3), actors=TOWNFOLK_SHOCK,
         cam=cam([7.0, 5.0, -21.8], [7.5, 4.8, -17.5], [7.2, 4.9, -20.6], snap=True)),
    # --- that night
    dict(id="S13a", t=W("n1"), light="night", actors={
        "Cube": {"cf": [4, 0, -27, 180], "to": [4, 0, -24.5, 180], "size": 3, "dur": 1.4, "face": "angry"}},
         cam=cam([4.5, 1.5, -14.5], [4, 2.0, -26], [4.5, 1.8, -17.5])),
    dict(id="S13b", t=W("n1", 5), actors={
        "Cube": {"cf": [4, 0, -6, 180], "size": 6, "size1": 26, "dur": 0.7, "face": "angry"},
        "Hero": H([2, 0.2, 12], [4, 0, -5], "scared", "scream")},
         cam=cam([-1.5, 1.4, 24], [3, 8, -5], [-3, 1.6, 32], [3, 13, -5], fov=68, shake=0.6)),
    dict(id="S13c", t=W("n1", 7), actors={
        "Cube": {"cf": [4, 0, -6, 180], "size": 26, "face": "angry"},
        "Hero": H([2, 0.2, 12], [4, 0, -5], "scared", "scream")},
         cam=cam([-6, 2, 52], [3, 14, -5], [-6, 9, 62], [3, 16, -5], fov=66)),
    dict(id="S14a", t=W("n2"), actors={
        "Cube": {"cf": [-88, 0.2, -10, 180], "size": 8, "face": "angry"},
        "Donut": {"cf": [-88, 0.2, -1.5, 180], "to": [-88, 1.0, -6.4, 180], "dur": 0.55, "delay": 0.25, "wobble": 10, "scale": 1.0, "ease": "in"}},
         cam=cam([-84.5, 3.5, 6], [-88, 4, -8], [-85.5, 3.6, 3], snap=True)),
    dict(id="S14b", t=W("n2", 4), actors={
        "Cube": {"cf": [-88, 0.2, -10, 180], "size": 8, "face": "angry"},
        "Abs": {"cf": [-88, 0.2, -1.5, 180], "to": [-88, 1.15, -6.3, 180], "dur": 0.5, "delay": 0.2, "wobble": 8, "scale": 1.1, "ease": "in"}},
         cam=cam([-91, 3.2, 4], [-88, 4, -8], [-90.4, 3.4, 2], snap=True, roll=-6)),
    dict(id="S14c", t=W("n2", 9), actors={
        "Cube": {"cf": [4, 0, -1, 0], "to": [4, 0, -8, 0], "size": 26, "dur": 2.0, "face": "angry"},
        "Hero": H([4.5, 0, -34], [4, 0, 0], "scared", "scream")},
         cam=cam([5.5, 2.2, -43], [4.5, 11, -10], [5.5, 2.0, -41.5], shake=0.25)),
    dict(id="S15", t=W("n3"), actors={
        "Cube": GIANT, "Hero": H([4.5, 0, -34], [4.5, 0, -60], "hips", "angry")},
         cam=cam([5, 3.4, -41.8], [4.5, 5.2, -33], [5, 3.8, -39.6])),
    # --- blender again
    dict(id="S16a", t=W("b1"), screen="horse", actors={
        "Hero": H([4, 0, -29.8], [4, 0, -60], "typing", "nervous"), **DESK_NIGHT},
         events=[{"at": W("b1", 5) - W("b1"), "actor": "Hero", "face": "shocked"},
                 {"at": W("b1", 6) - W("b1"), "actor": "Hero", "face": "cry"}],
         cam=cam([4.8, 5.6, -38.2], [4, 4.6, -30], [4.6, 5.3, -36.2])),
    dict(id="S16b", t=W("b1", 7), actors={
        "Hero": H([4, 0, -29.8], [4, 0, -60], "armsUp", "scream")},
         cam=cam([4.2, 4.8, -37.8], [4, 5.4, -30], [4.2, 4.9, -36.4], snap=True, roll=-8, shake=0.4)),
    dict(id="S17a", t=W("b2"), actors={
        "Hero": H([2.6, 0, -28], [4, 0, -10], "hips", "grin"),
        "Horse": {"cf": [13.5, 0, -29, 90], "to": [9, 0, -29, 90], "dur": 1.0, "wobble": 6, "scale": 1.0}},
         cam=cam([6, 4, -15.5], [6, 3.4, -29], [6, 3.8, -18])),
    dict(id="S17b", t=W("b2", 4), actors={
        "Horse": {"cf": [11.5, 0, -29, 90], "to": [8, 0, -29, 90], "dur": 1.4, "wobble": 5, "bob": 0.2, "scale": 1.0, "ease": "linear"}},
         cam=cam([11.2, 1.6, -21.5], [11.2, 1.8, -29], [8.2, 1.6, -21.5], [8.2, 1.8, -29], fov=58, ease="linear")),
    dict(id="S17c", t=W("b2", 7), actors={
        "Horse": {"cf": [9, 0, -29, 90], "dur": 2, "wobble": 3, "scale": 1.0}},
         cam=cam([18, 3.9, -28.4], [12, 3.6, -29], [16.6, 3.9, -28.6], snap=True)),
    dict(id="S18", t=W("b3"), actors={
        "Hero": H([-2.5, 0, -33.5], [8, 0, -24], "facepalm", "cry"),
        "Horse": {"cf": [5, 0, -30, 0], "to": [5, 1.3, -37.6, 0, -16, 13], "dur": 0.45, "ease": "in", "scale": 1.0},
        "Wall": {"cf": [5, 3.1, -41.6]}},
         cam=cam([15, 3.5, -34], [4, 3, -39], [14, 3.4, -34.5], shake=0.25)),
    # --- the fix: draw it → Vi3W
    dict(id="S19", t=W("v1"), actors={
        "Hero": H([4, 0, -30], [4, 0, -10], "hold", "grin"),
        "Paper": {"cf": [4, 3.15, -28.35]}},
         cam=cam([4.4, 4.7, -21], [4, 4.2, -30], [4.4, 4.5, -23.8])),
    dict(id="VI3W", t=W("v1", 11), actors={
        "Hero": H([4, 0, -30], [4, 0, -10], "hold", "grin"), "Paper": {"cf": [4, 3.15, -28.35]}},
         cam=cam([4.4, 4.5, -23.8], [4, 4.2, -30])),
    dict(id="S20", t=W("v2"), actors={
        "Cube": {"cf": [-16, 0, -4, 180], "size": 26, "face": "shocked"},
        "Hero": H([-2, 0.2, 18], [6, 0, -5], "scared", "shocked"),
        "Robot": [{"cf": [10, -32, -4, 200], "to": [10, 0, -4, 200], "h": 30, "dur": 0.8, "ease": "out"}]},
         cam=cam([0, 3.0, 46], [3, 14, -4], [0, 3.4, 52], [3, 15, -4], fov=70)),
    dict(id="S20R", t=W("v2", 3), actors={
        "Cube": {"cf": [-16, 0, -4, 180], "size": 26, "face": "shocked"},
        "Hero": H([-2, 0.2, 18], [6, 0, -5], "scared", "shocked"),
        "Robot": [{"cf": [10, 0, -4, 200], "h": 30}]},
         cam=cam([14, 1.4, 14], [10, 17, -4], [15, 1.3, 16], [10, 18, -4], fov=72, snap=True, shake=0.3)),
    dict(id="S21", t=W("v3"), actors={
        "Cube": {"cf": [-16, 0, -4, 180], "to": [-70, 220, -170, 180], "size": 26, "size1": 10, "dur": 1.4, "spin": 260, "ease": "in", "face": "scream"},
        "Hero": H([-2, 0.2, 18], [10, 0, 40], "cheer", "grin"),
        "Robot": [{"cf": [10, 0, -4, 200], "to": [10, 0, -4, 160, 0, -10], "h": 30, "dur": 0.35}]},
         cam=cam([34, 5, 46], [-12, 30, -40], [36, 4, 50], [-14, 34, -44], fov=80)),
    # --- ending
    dict(id="S22", t=W("e1"), light="morning", actors={
        "Lady": H([-36, 0.6, -18], [-20, 0, 40], "dance", "grin"),
        "Dude": H([-28, 0.6, -18], [-20, 0, 40], "dance2", "grin"),
        "Hero": H([-20, 0.6, -18], [-20, 0, 40], "cheer", "grin"),
        "Neighbor": H([-12, 0.6, -18], [-20, 0, 40], "dance3", "happy"),
        "Robot": [{"cf": [-32, 0.6, -18.5, 180], "h": 6, "bob": 0.6}, {"cf": [-24, 0.6, -18.5, 180], "h": 6, "bob": 0.6},
                  {"cf": [-16, 0.6, -18.5, 180], "h": 6, "bob": 0.6}]},
         cam=cam([-31, 4.6, -5], [-26, 4.6, -19], [-14, 4.6, -5], [-19, 4.6, -19], ease="linear", fov=55)),
    dict(id="S23", t=W("e2"), actors={
        "Mayor": H([104, 0.6, -20.5], [96, 0, -21.5], "search", "cry"),
        "Abs": {"cf": [112.5, 0.6, -17, 200], "to": [109, 0.6, -18.2, 200], "dur": 2.0, "bob": 0.15, "wobble": 5, "scale": 0.9}},
         cam=cam([104.5, 3.4, -10], [106.5, 2.9, -20], [105.2, 3.2, -12])),
]

TL = {"lead": 8, "end": round(M["dur"] + 0.3, 2), "roll90": False, "shots": SHOTS}
if __name__ == "__main__":
    (D / "studio").mkdir(exist_ok=True)
    (D / "studio/timeline.json").write_text(json.dumps(TL))
    print(len(SHOTS), "shots, end", TL["end"])
