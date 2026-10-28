import json
from pathlib import Path

import pytest

from reelforge.demo import BRIEF, demo_beats, write_glb
from reelforge.grid import Grid, timecode
from reelforge.llm import Decider, DecisionPending, submit_decision
from reelforge.ops import audio, glb, media, strokes
from reelforge.ops.capture import _subst
from reelforge.plan import apply_patch, beats_to_timeline, retime
from reelforge.project import BudgetExceeded, Project
from reelforge.review import merge
from reelforge.schemas import BeatsDoc, DimScore, Issue, Review, TimelineOp, Treatment
from reelforge.validate import validate_beats, validate_timeline


@pytest.fixture
def proj(tmp_path) -> Project:
    p = Project.create(tmp_path / "demo")
    p.path("brief.yaml").write_text(BRIEF)
    return p


def test_grid():
    g = Grid(120, 30)
    assert g.beat_frames == 15 and g.bar_frames == 60
    assert g.on_beat(240) and not g.on_beat(247)
    assert g.nearest_bar(119) == 120
    assert timecode(375) == "00:12.5"


def test_demo_beats_validate_and_build(proj):
    doc = BeatsDoc.model_validate(demo_beats())
    assert validate_beats(doc, proj.brief) == []
    tl = beats_to_timeline(doc, proj.brief, {})
    assert validate_timeline(tl, proj.brief) == []
    hero = tl.cut("hero")
    assert hero.durationInFrames == 360
    assert sum(s.duration for s in hero.scenes) == 360
    assert hero.scenes[2].props["headlines"][0]["text"] == "Sketch it."


def test_beats_validator_catches_problems(proj):
    raw = demo_beats()
    raw["cuts"][0]["beats"][1]["dur"] = 1.1          # off-grid + sum mismatch
    raw["cuts"][0]["beats"][2]["headline"] = "Sketch it with your BMW now"  # 6 words + trademark
    raw["cuts"][1]["beats"][0]["props"].pop("hook_at")
    raw["cuts"][1]["beats"][0]["dur"] = 2.0               # first social beat now outlasts the 1.5 s hook
    raw["cuts"][1]["beats"][1].update(start=2.0, dur=1.0)
    errs = validate_beats(BeatsDoc.model_validate(raw), proj.brief)
    text = "\n".join(errs)
    assert "off the beat grid" in text
    assert "more than 4 words" in text
    assert "trademark 'BMW'" in text
    assert "hook must land within 1.5s" in text


def test_monotone_and_sentinel_guard(proj):
    tl = beats_to_timeline(BeatsDoc.model_validate(demo_beats()), proj.brief, {})
    tl.cut("hero").scenes[2].props["timeKeys"] = [[0, 0], [60, 1], [30, 2]]
    tl.cut("hero").scenes[0].props["stare"] = 9999
    errs = validate_timeline(tl, proj.brief)
    assert any("not strictly increasing" in e for e in errs)
    assert any("sentinel" in e for e in errs)


def test_patch_with_scene_ids(proj):
    tl = beats_to_timeline(BeatsDoc.model_validate(demo_beats()), proj.brief, {})
    doc = tl.model_dump(by_alias=True, mode="json")
    out = apply_patch(doc, [
        TimelineOp(op="replace", path="/cuts/hero/scenes/s03/props/headlines", value=[{"text": "Draw it.", "at": 4}]),
        TimelineOp(op="replace", path="/cuts/hero/scenes/s01/duration", value=45),
        TimelineOp(op="replace", path="/cuts/hero/scenes/s02/duration", value=45),
    ])
    out = retime(out, "hero")
    hero = next(c for c in out["cuts"] if c["name"] == "hero")
    assert hero["scenes"][2]["props"]["headlines"][0]["text"] == "Draw it."
    assert [s["from"] for s in hero["scenes"]][:3] == [0, 45, 90]


def test_merge_lower_counts():
    d = lambda dim, s: DimScore(dimension=dim, score=s, evidence=["00:01.0 16x9"])
    a = Review(scores=[d("hook", 8), d("story", 7)], issues=[], summary="")
    b = Review(scores=[d("hook", 6), d("story", 7.6)],
               issues=[Issue(id="i1", severity="medium", timecode="00:02.0", problem="x", fix="y", tag="craft", gain=3, effort=1)],
               summary="")
    m = merge(a, b)
    assert m["dimensions"]["hook"] == 6          # differ by 2 -> lower counts
    assert m["dimensions"]["story"] == 7.3       # within 1 -> average
    assert m["blocking"] == 1


def test_solve_segments_delay_and_trim():
    segs = audio.solve_segments([
        {"src": "m.mp3", "edit_from": 0, "edit_to": 52.85, "edit_align": 8.0, "music_align": 6.85},
        {"src": "m.mp3", "edit_from": 52.85, "edit_to": 80, "edit_align": 62.0, "music_align": 40.0},
    ])
    assert abs(segs[0]["from"] - 1.15 * 30) <= 0.5 and segs[0]["trimSec"] == 0.0   # delayed 1.15 s onto the sting
    assert abs(segs[1]["from"] - 52.85 * 30) <= 0.5 and abs(segs[1]["trimSec"] - 30.85) < 1e-6


def test_glb_inspect_and_anchors(tmp_path):
    f = tmp_path / "car.glb"
    write_glb(f)
    info = glb.inspect_glb(f)
    assert info["bounds"]["extent"][0] == pytest.approx(4.4, abs=1e-3)
    assert info["up_axis_guess"] == "y"
    a = glb.anchors(f)
    assert len(a["anchors"]) == 4 and a["length_axis"] == "x"
    for v in a["anchors"].values():
        assert v[1] < -0.1  # lowest vertices -> below centre


def test_strokes_deterministic():
    a = strokes.build(strokes.TEMPLATES["sedan_side"], seed=5)
    b = strokes.build(strokes.TEMPLATES["sedan_side"], seed=5)
    c = strokes.build(strokes.TEMPLATES["sedan_side"], seed=6)
    assert a == b and a != c
    assert all(0 <= x <= 1 and 0 <= y <= 1 for s in a for x, y in s)


def test_capture_macro_substitution():
    steps = _subst({"action": "draw", "strokes": "{strokes}", "text": "make it a {prompt}"},
                   {"strokes": [[[0, 0], [1, 1]]], "prompt": "sports car"})
    assert steps["strokes"] == [[[0, 0], [1, 1]]] and steps["text"] == "make it a sports car"


def test_srt():
    s = media.srt([(30, 75, "Draw what you mean")])
    assert "00:00:01,000 --> 00:00:02,500" in s


def test_agent_mode_decision_roundtrip(proj):
    d = Decider(proj, mode="agent")
    with pytest.raises(DecisionPending) as e:
        d.decide("D1_treatment", Treatment, "task", {"x": 1})
    req = json.loads(e.value.request_path.read_text())
    assert "output_schema" in req and req["decision"] == "D1_treatment"
    good = {"logline": "l", "tone": "t", "motif": "m", "colour_script": [], "camera_language": "c", "music_plan": "m",
            "pacing_targets": [], "hook_rule": "h", "screenshot_frames": [], "steal_list": [], "treatment_markdown": "# t"}
    submit_decision(proj, "D1_treatment", {**good, "bogus": 1})        # schema-invalid: extra field
    with pytest.raises(DecisionPending) as e2:
        d.decide("D1_treatment", Treatment, "task", {"x": 1})
    assert json.loads(e2.value.request_path.read_text())["context"]["_previous_attempt_errors"]
    submit_decision(proj, "D1_treatment", good)
    out = d.decide("D1_treatment", Treatment, "task", {"x": 1})
    assert out.motif == "m"
    assert d.decide("D1_treatment", Treatment, "task", {"x": 1}).motif == "m"  # cached by input hash
    assert proj.read_log("decisions")[-1]["decision"] == "D1_treatment"


def test_budget_enforced(proj):
    proj.add_cost("fal", 0.0)
    with pytest.raises(BudgetExceeded):
        proj.check_budget("fal", est_usd=0.01)   # demo brief has fal_usd: 0
