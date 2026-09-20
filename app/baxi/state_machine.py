from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
from .animation_manifest import AnimationSpec, load_all_v0_9

class BaxiState(str, Enum):
    IDLE = "idle"
    OBSERVE_SIT = "observe_sit"
    WALK_LEFT = "walk_left"
    WALK_RIGHT = "walk_right"
    GROOM_PAW = "groom_paw"
    STRETCH_FRONT = "stretch_front"
    FEED_CAN = "feed_can"
    DANCE_01 = "dance_01"
    DANCE_02 = "dance_02"
    DANCE_03 = "dance_03"
    DANCE_04 = "dance_04"
    DANCE_05 = "dance_05"

@dataclass
class RuntimeConfig:
    idle_min_seconds: float = 5.0
    idle_max_seconds: float = 12.0
    walk_left_probability: float = 0.12
    walk_right_probability: float = 0.12
    observe_sit_probability: float = 0.08
    stretch_front_probability: float = 0.05
    groom_paw_probability: float = 0.05
    dance_after_feed_probabilities: tuple[float, float, float, float, float] = (0.05, 0.10, 0.20, 0.35, 1.0)

class PendingActionError(RuntimeError):
    """Raised when a UX entry exists but its final frame package is not integrated."""

class BaxiStateMachine:
    """Baxi v0.9 runtime state chain with feed/dance Veo actions integrated.

    Active actions: idle / observe_sit / walk_left / walk_right / groom_paw /
    stretch_front / feed_can / dance_01..dance_05. Feed/dance are manual
    right-click one-shot entries; all manual actions return to idle after a short final-frame hold.

    Feed-can constraint from Red: use an already-opened, lidless can only. Do not
    include closed-can, lid, or pull-ring stages in the runtime/video entry path
    because they complicate cutout and increase clipping/intersection risk.
    """
    PENDING_STATES = {
        BaxiState.FEED_CAN,
        BaxiState.DANCE_01,
        BaxiState.DANCE_02,
        BaxiState.DANCE_03,
        BaxiState.DANCE_04,
        BaxiState.DANCE_05,
    }

    def __init__(self, config: RuntimeConfig | None = None):
        self.config = config or RuntimeConfig()
        self.state = BaxiState.IDLE
        self._animations = load_all_v0_9()

    def choose_next_after_idle(self) -> BaxiState:
        roll = random.random()
        if roll < self.config.observe_sit_probability:
            return BaxiState.OBSERVE_SIT
        roll -= self.config.observe_sit_probability
        if roll < self.config.stretch_front_probability:
            return BaxiState.STRETCH_FRONT
        roll -= self.config.stretch_front_probability
        if roll < self.config.groom_paw_probability:
            return BaxiState.GROOM_PAW
        roll -= self.config.groom_paw_probability
        if roll < self.config.walk_left_probability:
            return BaxiState.WALK_LEFT
        roll -= self.config.walk_left_probability
        if roll < self.config.walk_right_probability:
            return BaxiState.WALK_RIGHT
        return BaxiState.IDLE

    def next_after_complete(self, state: BaxiState) -> BaxiState:
        one_shot_states = {
            BaxiState.OBSERVE_SIT,
            BaxiState.GROOM_PAW,
            BaxiState.STRETCH_FRONT,
            BaxiState.FEED_CAN,
            BaxiState.DANCE_01,
            BaxiState.DANCE_02,
            BaxiState.DANCE_03,
            BaxiState.DANCE_04,
            BaxiState.DANCE_05,
        }
        if state in one_shot_states:
            return BaxiState.IDLE
        return state

    def available_states(self) -> set[BaxiState]:
        return {BaxiState(key) for key in self._animations}

    def is_pending(self, state: BaxiState) -> bool:
        return state in self.PENDING_STATES and state.value not in self._animations

    def require_integrated(self, state: BaxiState) -> None:
        if self.is_pending(state):
            raise PendingActionError(
                f"{state.value} 已预留入口，但最终切帧包尚未接入；需先通过资源校验后再播放"
            )

    def click_feedback(self) -> AnimationSpec:
        """Hidden/manual interaction entry: play the paw-groom response once."""
        return self.enter(BaxiState.GROOM_PAW)

    def stretch_once(self) -> AnimationSpec:
        """Manual/debug entry for the one-shot front stretch action."""
        return self.enter(BaxiState.STRETCH_FRONT)

    def feed_can_once(self) -> AnimationSpec:
        """Right-click menu entry: opened/lidless can feeding only."""
        return self.enter(BaxiState.FEED_CAN)

    def choose_dance_after_feed(self, feed_count: int) -> BaxiState | None:
        """Feed trigger policy approved for hotfix2+: first 4 feeds may dance early; 5th is guaranteed.

        On early trigger, choose among dance_01..dance_04 randomly. On the fifth feed,
        force dance_05. The caller owns persistence/reset of feed_count so the
        policy survives app restarts.
        """
        normalized_count = min(max(1, feed_count), 5)
        if normalized_count >= 5:
            return BaxiState.DANCE_05
        probability = self.config.dance_after_feed_probabilities[normalized_count - 1]
        if random.random() < probability:
            return BaxiState(f"dance_{random.randint(1, 4):02d}")
        return None

    def dance_once(self, index: int) -> AnimationSpec:
        """Right-click menu entry for dance_01..dance_05."""
        if not 1 <= index <= 5:
            raise ValueError(f"dance index must be 1..5, got {index}")
        return self.enter(BaxiState(f"dance_{index:02d}"))

    def enter(self, state: BaxiState) -> AnimationSpec:
        self.require_integrated(state)
        self.state = state
        return self._animations[state.value]
