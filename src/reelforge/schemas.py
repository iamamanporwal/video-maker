"""Data contracts. Every file the pipeline reads or writes, and every AI decision output, is one of these."""

from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

Format = Literal["16x9", "9x16", "4x5", "5x4"]

FORMAT_SIZES: dict[str, tuple[int, int]] = {
    "16x9": (1920, 1080),
    "9x16": (1080, 1920),
    "4x5": (1080, 1350),
    "5x4": (1350, 1080),
}

SCENE_KINDS = (
    "cold_open", "chat", "url_to_logo", "product_shot", "before_after", "triptych",
    "image_to_3d", "plot_twist", "finale_3d", "end_room", "end_card", "video_clip", "photo_insert",
)
SceneKind = Literal[
    "cold_open", "chat", "url_to_logo", "product_shot", "before_after", "triptych",
    "image_to_3d", "plot_twist", "finale_3d", "end_room", "end_card", "video_clip", "photo_insert", "hook",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- inputs


class Auth(BaseModel):
    method: Literal["test_token", "storage_state", "none"] = "none"
    script: Optional[str] = None
    storage_state: Optional[str] = None
    local_storage_key: str = "auth_token"


class Product(BaseModel):
    name: str
    url: str
    auth: Auth = Auth()


class Cut(BaseModel):
    name: str
    seconds: float
    formats: list[Format]
    hook_seconds: Optional[float] = None


class Music(BaseModel):
    bpm: int = 120
    mood: str = ""


class Budgets(BaseModel):
    app_credits: int = 600
    fal_usd: float = 10.0
    llm_usd: float = 25.0
    max_iterations: int = 10
    target_score: float = 9.0


class Rules(BaseModel):
    trademark_avoid: list[str] = []
    honesty_labels: bool = True
    max_headline_words: int = 4


class Brief(BaseModel):
    project: str
    genre: str = "product-launch"  # taste research is cached per genre, not per film
    product: Product
    idea: str
    story: Union[str, list[str]]
    tagline: str
    setting: str = ""
    cuts: list[Cut]
    voiceover: bool = False
    music: Music = Music()
    providers: dict[str, str] = {}
    budgets: Budgets = Budgets()
    rules: Rules = Rules()
    fps: int = 30

    @field_validator("project")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("project must be a slug (letters, digits, - and _)")
        return v


class Brand(BaseModel):
    colors: dict[str, Any]
    accent_rules: str = ""
    fonts: dict[str, str] = {"display": "Urbanist:800", "body": "Urbanist:600", "mono": "JetBrains Mono:400"}
    tracking: dict[str, str] = {"headline": "-0.035em"}
    motion: dict[str, Any] = {"default_ease": "outExpo", "ui_spring": {"damping": 13}, "linear_allowed": ["caret", "camera_drift"]}
    logo: dict[str, str] = {}
    motif: str = ""


class Asset(BaseModel):
    file: str
    kind: Literal["logo", "music", "sfx", "hdri", "photo", "video", "image", "font", "glb", "other"]
    use: list[str] = []
    never: list[str] = []
    licence: Optional[str] = None
    notes: Optional[str] = None
    generated: bool = False

    @property
    def id(self) -> str:
        return self.file


# --------------------------------------------------------------------------- plan data


class Beat(_Strict):
    id: str
    start: float = Field(description="seconds from the start of the cut")
    dur: float = Field(description="seconds")
    kind: SceneKind
    headline: str = Field("", description="on-screen headline copy, <= 4 words")
    caption: str = ""
    sfx_hints: list[str] = []
    music_section: str = ""
    props: dict[str, Any] = {}


class CutBeats(_Strict):
    cut: str
    beats: list[Beat]


class BeatsDoc(_Strict):
    bpm: int
    cuts: list[CutBeats]


class Scene(BaseModel):
    id: str
    kind: SceneKind
    from_: int = Field(alias="from")
    duration: int
    props: dict[str, Any] = {}
    model_config = ConfigDict(populate_by_name=True)


class MusicSegment(BaseModel):
    src: str
    from_: int = Field(alias="from")
    trimSec: float = 0.0
    dur: int
    volumeKeys: list[tuple[int, float]] = []
    model_config = ConfigDict(populate_by_name=True)


class VoiceLine(BaseModel):
    src: str
    from_: int = Field(alias="from")
    vol: float = 1.0
    words: list[tuple[int, int, str]] = Field(default=[], description="[fromFrame, toFrame, word] in cut frames (real TTS timings)")
    capY: Optional[float] = Field(default=None, description="caption centre as a fraction of frame height")
    caption: bool = True
    model_config = ConfigDict(populate_by_name=True)


class CutTimeline(BaseModel):
    name: str
    fps: int = 30
    durationInFrames: int
    formats: list[Format]
    bpm: int = 120
    scenes: list[Scene]
    sfx: list[tuple[int, str, float, float]] = Field(default=[], description="[frame, name, vol, durSec]")
    captions: list[tuple[int, int, str]] = Field(default=[], description="[fromFrame, toFrame, text]")
    music: list[MusicSegment] = []
    voice: list[VoiceLine] = Field(default=[], description="voiceover lines; music ducks under them")


class Timeline(BaseModel):
    version: int = 1
    project: str
    brand: dict[str, Any] = {}
    cuts: list[CutTimeline]

    def cut(self, name: str) -> CutTimeline:
        for c in self.cuts:
            if c.name == name:
                return c
        raise KeyError(name)


# --------------------------------------------------------------------------- AI decision outputs (D1-D11)


class ColourAct(_Strict):
    act: str
    palette: list[str]
    note: str


class Treatment(_Strict):
    """D1"""
    logline: str
    tone: str
    motif: str
    colour_script: list[ColourAct]
    camera_language: str
    music_plan: str
    pacing_targets: list[str]
    hook_rule: str
    screenshot_frames: list[str]
    steal_list: list[str] = Field(description="taste board: what to steal and from whom")
    treatment_markdown: str


class CaptureStep(_Strict):
    take: str = Field(description="take id, e.g. 'sedan_sketch'")
    command: Literal["sketch", "edit", "to3d", "look", "models", "type", "click", "wait"]
    beat_ids: list[str]
    prompt: str = Field("", description="text typed on screen; trademark rules apply")
    features: list[str] = Field(default=[], description="what to sketch, e.g. 'sedan side profile'")
    model: str = Field("", description="model choice, matched by regex in the UI")
    source_take: str = Field("", description="for edit/to3d: the take whose real out.jpg is used")
    new_studio: bool = True
    variants: int = 1


class CapturePlan(_Strict):
    """D3"""
    steps: list[CaptureStep]
    notes: str = ""


class Part(_Strict):
    name: str
    kind: Literal["circle", "line", "polyline", "point"]
    points: list[tuple[float, float]] = Field(description="pixel coords in out.jpg")
    radius: float = 0.0


class StrokePlacement(_Strict):
    """D4"""
    image_size: tuple[int, int]
    parts: list[Part]


class CheckResult(_Strict):
    check: str
    passed: bool
    note: str = ""


class VariantVerdict(_Strict):
    id: str
    checks: list[CheckResult]


class VariantJudgement(_Strict):
    """D5"""
    best: Optional[str]
    reasons: str
    verdicts: list[VariantVerdict]
    rejects: list[str]
    stronger_prompt: str = Field("", description="if all rejected: a strengthened prompt for the retry")


class MusicSection(_Strict):
    section_name: str
    positive_local_styles: list[str]
    negative_local_styles: list[str]
    duration_ms: int
    lines: list[str] = []


class SfxCue(_Strict):
    name: str
    prompt: str
    seconds: float


class VideoPrompt(_Strict):
    clip: str
    beat_id: str
    prompt: str
    seconds: float
    aspect: Literal["16:9", "9:16", "1:1"]
    candidates: int = 2


class AudioPlan(_Strict):
    """D6"""
    positive_global_styles: list[str]
    negative_global_styles: list[str]
    sections: list[MusicSection]
    outro_sections: list[MusicSection]
    sfx: list[SfxCue]
    video: list[VideoPrompt] = []


class AssetPick(_Strict):
    beat_id: str
    asset: Optional[str]
    reason: str


class AssetSelection(_Strict):
    """D7"""
    picks: list[AssetPick]


DIMENSIONS = (
    ("hook", 0.12), ("story", 0.12), ("product_clarity", 0.14), ("before_after", 0.10),
    ("motion", 0.10), ("visual_design", 0.10), ("finale_3d", 0.08), ("pacing_sync", 0.10),
    ("format_adaptation", 0.07), ("tech_honesty", 0.07),
)


class DimScore(_Strict):
    dimension: str
    score: float = Field(ge=0, le=10)
    evidence: list[str] = Field(description="each item cites a timecode like '00:12.5 16x9 hero'")


class Issue(_Strict):
    id: str
    severity: Literal["low", "medium", "high"]
    timecode: str
    problem: str
    fix: str
    tag: Literal["craft", "real-output-bound", "missing-asset"]
    gain: float = Field(ge=0, le=10)
    effort: float = Field(ge=0.1, le=10)


class Review(_Strict):
    """D8 (self) and D9 (fresh reviewer)"""
    scores: list[DimScore]
    issues: list[Issue]
    summary: str


class TimelineOp(_Strict):
    op: Literal["replace", "add", "remove"]
    path: str = Field(description="JSON-pointer into timeline.json, e.g. /cuts/0/scenes/3/props/headline")
    value: Any = None


class Recapture(_Strict):
    take: str
    reason: str
    prompt: str = ""


class FixPlan(_Strict):
    """D10"""
    apply: list[str] = Field(description="issue ids being fixed")
    skip: list[str]
    patch: list[TimelineOp]
    recapture: list[Recapture] = []
    approach_change: str = Field("", description="non-empty when changing approach on a stuck dimension")
    needs_asset: list[str] = Field(default=[], description="assets to ask the human for when they are the ceiling")
    rationale: str


class DirectorNote(_Strict):
    """D11"""
    markdown: str
