from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sys

def _default_asset_root() -> Path:
    # Normal source run: app/baxi/animation_manifest.py -> app/assets/baxi
    source_root = Path(__file__).resolve().parents[1] / "assets" / "baxi"
    # PyInstaller one-dir/one-file: data is placed under sys._MEIPASS/assets/baxi.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        frozen_root = Path(sys._MEIPASS) / "assets" / "baxi"
        if frozen_root.exists():
            return frozen_root
    return source_root

ASSET_ROOT = _default_asset_root()

@dataclass(frozen=True)
class FrameSpec:
    index: int
    path: Path
    bbox_xywh: tuple[int, int, int, int]
    foot_anchor: tuple[int, int]
    source_frame: int | None = None
    phase: str = "main"
    sha256: str | None = None

@dataclass(frozen=True)
class AnimationSpec:
    key: str
    direction: str
    fps: int
    loop_mode: str
    canvas: tuple[int, int]
    foot_anchor: tuple[int, int]
    frames: tuple[FrameSpec, ...]

class ManifestError(RuntimeError):
    pass

def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ManifestError(f"无法读取 manifest: {path}: {exc}") from exc

def _load_action(asset_root: Path, action: str, version: str, expected_count: int) -> AnimationSpec:
    """Load Baxi v0.6 action assets from the isolated Baxi namespace.

    Source manifest bbox_out is xywh, not x1/y1/x2/y2. Runtime keeps it as xywh
    and does not rescale frames at load time.
    """
    base = asset_root / "actions" / f"{action}_{version}"
    manifest = _read_json(base / "source_manifest.json")
    canvas = tuple(int(v) for v in manifest["canvas"])
    anchor = tuple(int(v) for v in manifest["foot_anchor"])
    manifest_frames = manifest["frames"]
    if len(manifest_frames) != expected_count:
        raise ManifestError(f"{action}_{version} 帧数不符: {len(manifest_frames)} != {expected_count}")
    frames: list[FrameSpec] = []
    for frame in manifest_frames:
        rel = Path(frame["file"])
        path = base / rel
        frames.append(FrameSpec(
            index=int(frame["frame"]),
            path=path,
            bbox_xywh=tuple(int(v) for v in frame["bbox_out"]),
            foot_anchor=tuple(int(v) for v in frame["foot_anchor"]),
            source_frame=frame.get("source_frame"),
            phase=str(frame.get("phase", "main")),
            sha256=frame.get("sha256"),
        ))
    direction = "left" if action.endswith("left") else "right" if action.endswith("right") else "center"
    return AnimationSpec(
        key=f"baxi.{action.replace('_', '.')}.{version}",
        direction=direction,
        fps=int(manifest.get("fps_suggested", 12)),
        loop_mode=str(manifest.get("looping", "soft_loop")),
        canvas=canvas,
        foot_anchor=anchor,
        frames=tuple(frames),
    )

def load_idle_v0_6(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "idle", "v0_6", 16)

def load_observe_sit_v0_6(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "observe_sit", "v0_6", 18)

def load_walk_left_v0_6(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "walk_left", "v0_6", 18)

def load_walk_right_v0_6(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "walk_right", "v0_6", 18)

def load_groom_paw_v0_7(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "groom_paw", "v0_7", 18)

def load_stretch_front_v0_7(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "stretch_front", "v0_7", 16)

def load_feed_can_v0_9(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "feed_can", "v0_9", 16)

def load_dance_01_v0_9(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "dance_01", "v0_9", 18)

def load_dance_02_v0_9(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "dance_02", "v0_9", 18)

def load_dance_03_v0_9(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "dance_03", "v0_9", 18)

def load_dance_04_v0_9(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "dance_04", "v0_9", 18)

def load_dance_05_v0_9(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return _load_action(asset_root, "dance_05", "v0_9", 18)

def load_all_v0_9(asset_root: Path = ASSET_ROOT) -> dict[str, AnimationSpec]:
    return {
        "idle": load_idle_v0_6(asset_root),
        "observe_sit": load_observe_sit_v0_6(asset_root),
        "walk_left": load_walk_left_v0_6(asset_root),
        "walk_right": load_walk_right_v0_6(asset_root),
        "groom_paw": load_groom_paw_v0_7(asset_root),
        "stretch_front": load_stretch_front_v0_7(asset_root),
        "feed_can": load_feed_can_v0_9(asset_root),
        "dance_01": load_dance_01_v0_9(asset_root),
        "dance_02": load_dance_02_v0_9(asset_root),
        "dance_03": load_dance_03_v0_9(asset_root),
        "dance_04": load_dance_04_v0_9(asset_root),
        "dance_05": load_dance_05_v0_9(asset_root),
    }

def load_all_v0_7(asset_root: Path = ASSET_ROOT) -> dict[str, AnimationSpec]:
    # v0.9 is backwards-compatible and adds final feed/dance Veo-derived actions.
    return load_all_v0_9(asset_root)

def load_all_v0_6(asset_root: Path = ASSET_ROOT) -> dict[str, AnimationSpec]:
    # v0.7 is backwards-compatible with the v0.6 formal action set and adds
    # two one-shot return-to-idle actions. Keep the old function name for
    # scripts that still import it.
    return load_all_v0_7(asset_root)

# Compatibility aliases for older smoke scripts / test harnesses in prior bundles.
def load_walk_right_v0_5a(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return load_walk_right_v0_6(asset_root)

def load_walk_right_v0_5(asset_root: Path = ASSET_ROOT) -> AnimationSpec:
    return load_walk_right_v0_6(asset_root)
