from __future__ import annotations

from pathlib import Path
import hashlib
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from baxi.animation_manifest import load_all_v0_9
from baxi.state_machine import BaxiState, BaxiStateMachine, PendingActionError

EXPECTED = {
    "idle": {"key": "baxi.idle.v0_6", "frames": 16, "fps": 6, "loop_contains": "soft_loop"},
    "observe_sit": {"key": "baxi.observe.sit.v0_6", "frames": 18, "fps": 6, "loop_contains": "one_shot_return_idle"},
    "walk_left": {"key": "baxi.walk.left.v0_6", "frames": 18, "fps": 6, "loop_contains": "soft_loop"},
    "walk_right": {"key": "baxi.walk.right.v0_6", "frames": 18, "fps": 6, "loop_contains": "soft_loop"},
    "groom_paw": {"key": "baxi.groom.paw.v0_7", "frames": 18, "fps": 6, "loop_contains": "one_shot_return_idle"},
    "stretch_front": {"key": "baxi.stretch.front.v0_7", "frames": 16, "fps": 6, "loop_contains": "one_shot_return_idle"},
    "feed_can": {"key": "baxi.feed.can.v0_9", "frames": 16, "fps": 5, "loop_contains": "one_shot_return_idle"},
    "dance_01": {"key": "baxi.dance.01.v0_9", "frames": 18, "fps": 6, "loop_contains": "one_shot_return_idle"},
    "dance_02": {"key": "baxi.dance.02.v0_9", "frames": 18, "fps": 6, "loop_contains": "one_shot_return_idle"},
    "dance_03": {"key": "baxi.dance.03.v0_9", "frames": 18, "fps": 6, "loop_contains": "one_shot_return_idle"},
    "dance_04": {"key": "baxi.dance.04.v0_9", "frames": 18, "fps": 6, "loop_contains": "one_shot_return_idle"},
    "dance_05": {"key": "baxi.dance.05.v0_9", "frames": 18, "fps": 6, "loop_contains": "one_shot_return_idle"},
}

ONE_SHOTS = {
    BaxiState.OBSERVE_SIT, BaxiState.GROOM_PAW, BaxiState.STRETCH_FRONT,
    BaxiState.FEED_CAN, BaxiState.DANCE_01, BaxiState.DANCE_02, BaxiState.DANCE_03, BaxiState.DANCE_04, BaxiState.DANCE_05,
}

def main() -> int:
    specs = load_all_v0_9(ROOT / "app" / "assets" / "baxi")
    errors: list[str] = []
    if set(specs) != set(EXPECTED):
        errors.append(f"formal actions mismatch {sorted(specs)} != {sorted(EXPECTED)}")
    for action, exp in EXPECTED.items():
        spec = specs.get(action)
        if spec is None:
            continue
        if spec.key != exp["key"]: errors.append(f"{action}: wrong key {spec.key}")
        if spec.fps != exp["fps"]: errors.append(f"{action}: fps expected {exp['fps']} got {spec.fps}")
        if exp["loop_contains"] not in spec.loop_mode: errors.append(f"{action}: loop mode {spec.loop_mode!r}")
        if spec.canvas != (1024, 1024): errors.append(f"{action}: canvas expected 1024x1024 got {spec.canvas}")
        if spec.foot_anchor != (512, 914): errors.append(f"{action}: anchor expected 512,914 got {spec.foot_anchor}")
        if len(spec.frames) != exp["frames"]: errors.append(f"{action}: frame count expected {exp['frames']} got {len(spec.frames)}")
        for expected_index, frame in enumerate(spec.frames, 1):
            if frame.index != expected_index:
                errors.append(f"{action}: frame index discontinuity: expected {expected_index} got {frame.index}")
            if frame.foot_anchor != spec.foot_anchor:
                errors.append(f"{action} frame {expected_index}: anchor mismatch {frame.foot_anchor}")
            if not frame.path.exists():
                errors.append(f"{action} missing frame {frame.path}")
                continue
            im = Image.open(frame.path)
            if im.mode != "RGBA": errors.append(f"{action} {frame.path.name}: mode {im.mode}, expected RGBA")
            if im.size != spec.canvas: errors.append(f"{action} {frame.path.name}: size {im.size}, expected {spec.canvas}")
            alpha = im.getchannel("A")
            if alpha.getextrema()[1] == 0: errors.append(f"{action} {frame.path.name}: fully transparent")
            bbox = alpha.getbbox()
            x, y, w, h = frame.bbox_xywh
            if bbox != (x, y, x + w, y + h):
                errors.append(f"{action} {frame.path.name}: alpha bbox {bbox} != manifest xywh {(x,y,w,h)}")
            if frame.sha256 and hashlib.sha256(frame.path.read_bytes()).hexdigest() != frame.sha256:
                errors.append(f"{action} {frame.path.name}: sha256 mismatch")
            if bbox and bbox[3] > spec.foot_anchor[1] + 1:
                errors.append(f"{action} {frame.path.name}: alpha extends below baseline: bbox bottom {bbox[3]}")
    sm = BaxiStateMachine()
    for state in [BaxiState(key) for key in EXPECTED]:
        if sm.is_pending(state):
            errors.append(f"{state.value}: unexpectedly pending after v0.9 integration")
        spec = sm.enter(state)
        if spec.key != EXPECTED[state.value]["key"]:
            errors.append(f"state {state.value}: entered {spec.key}")
    for one_shot in ONE_SHOTS:
        if sm.next_after_complete(one_shot) is not BaxiState.IDLE:
            errors.append(f"{one_shot.value} does not return idle")
    if sm.next_after_complete(BaxiState.DANCE_04) is not BaxiState.IDLE:
        errors.append("dance_04 does not return idle")
    if sm.click_feedback().key != EXPECTED["groom_paw"]["key"]:
        errors.append("click feedback does not enter groom_paw")
    if sm.feed_can_once().key != EXPECTED["feed_can"]["key"]:
        errors.append("feed_can_once does not enter feed_can")
    for idx in range(1, 6):
        if sm.dance_once(idx).key != EXPECTED[f"dance_{idx:02d}"]["key"]:
            errors.append(f"dance_once({idx}) wrong action")
    for bad_index in (0, 6):
        try:
            sm.dance_once(bad_index)
        except ValueError:
            pass
        except PendingActionError:
            errors.append(f"dance_once({bad_index}) checked integration before index validation")
        else:
            errors.append(f"dance_once({bad_index}) did not reject invalid index")
    if errors:
        print("FAIL")
        for e in errors:
            print("-", e)
        return 1
    print("PASS baxi v0.9-shakefix3 runtime: 12 actions loaded, fixed 1024 canvas, anchor 512,914, bbox xywh matches alpha, no scaling/non-uniform stretch in assets, shakefix3 groom_paw and dance_01 integrated over shakefix1 baseline, all one-shots return idle")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
