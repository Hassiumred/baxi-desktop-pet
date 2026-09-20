from __future__ import annotations

try:
    from PySide6.QtCore import Qt, QTimer, QPoint, QSettings, QSize
    from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter
    from PySide6.QtWidgets import QApplication, QLabel, QMenu, QSystemTrayIcon
except Exception:  # PySide6 may be absent in Linux CI; import app modules without GUI.
    Qt = QTimer = QPoint = QSettings = QSize = QAction = QIcon = QPixmap = QPainter = QApplication = QLabel = QMenu = QSystemTrayIcon = None

from .animation_manifest import AnimationSpec
from .state_machine import BaxiState, BaxiStateMachine, PendingActionError


FINAL_HOLD_MS = 170
IDLE_BLEND_FRAMES = 6  # v0.9 transition guard: fade one-shot final pose into idle; no bbox fit/scale
IDLE_BLEND_FPS = 12
GROOM_IDLE_TARGET_FRAME_INDEX = 0  # rescue1: keep target at idle f1 and blend instead of direct hard cut
WALK_LOOP_COUNT = 2  # play a short left/right walk burst, then return to idle
WALK_STEP_PX = 4  # actual desktop-window movement per rendered walk frame
CANONICAL_CANVAS = (1024, 1024)
CANONICAL_FOOT_ANCHOR = (512, 914)
SHAKEFIX1_FIXED_CANVAS_RENDERING = True  # draw every frame into the same 1024x1024 viewport; never auto-fit alpha bbox
MIN_DISPLAY_SCALE = 0.35
MAX_DISPLAY_SCALE = 1.40
DISPLAY_SCALE_STEP = 0.10
DEFAULT_DISPLAY_SCALE = 0.55
SIZE_PRESETS = {
    "small": 0.45,
    "medium": 0.55,
    "large": 0.70,
}
SIZE_PRESET_LABELS = {
    "small": "小",
    "medium": "中",
    "large": "大",
}



class BaxiPetWindow(QLabel):
    def __init__(self, animation: AnimationSpec | None = None):
        if QLabel is None:
            raise RuntimeError("PySide6 is not installed")
        super().__init__()
        self.state_machine = BaxiStateMachine()
        self.animation = animation or self.state_machine.enter(BaxiState.IDLE)
        self.frame_index = 0
        self._drag_offset: QPoint | None = None
        self.tray: QSystemTrayIcon | None = None
        self.settings = QSettings("Offloop", "BaxiDesktopPet")
        self.display_scale = self._load_display_scale()
        self.diagnostics_enabled = False
        self.feed_dance_count = self._load_feed_dance_count()
        self._last_rendered_size = QSize(1, 1)
        self._transition_from_frame = None
        self._transition_frame_index = 0
        self._transition_total_frames = 0
        self._transition_target_state: BaxiState | None = None
        self._transition_target_frame_index = 0
        self._walk_completed_loops = 0

        self.setWindowTitle("八喜桌宠")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setScaledContents(False)  # runtime must not compensate asset differences by per-frame scaling
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self._restart_timer()
        self.next_frame()
        self._setup_tray()

    def _restart_timer(self):
        interval = max(1, round(1000 / self.animation.fps))
        self.timer.start(interval)

    def _enter(self, state: BaxiState):
        self.animation = self.state_machine.enter(state)
        self.frame_index = 0
        self._walk_completed_loops = 0
        self._restart_timer()
        self.next_frame()

    def _is_one_shot(self) -> bool:
        return "one_shot_return_idle" in self.animation.loop_mode

    def _is_walk_state(self) -> bool:
        return self.state_machine.state in {BaxiState.WALK_LEFT, BaxiState.WALK_RIGHT}

    def _advance_walk_position(self):
        if not self._is_walk_state():
            return
        direction = -1 if self.state_machine.state is BaxiState.WALK_LEFT else 1
        target = self.pos() + QPoint(direction * WALK_STEP_PX, 0)
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            max_x = max(available.left(), available.right() - self.width() + 1)
            x = min(max(target.x(), available.left()), max_x)
            y = min(max(target.y(), available.top()), max(available.top(), available.bottom() - self.height() + 1))
            target = QPoint(x, y)
        self.move(target)

    def _load_display_scale(self) -> float:
        try:
            raw = float(self.settings.value("display_scale", DEFAULT_DISPLAY_SCALE))
        except Exception:
            raw = DEFAULT_DISPLAY_SCALE
        return max(MIN_DISPLAY_SCALE, min(MAX_DISPLAY_SCALE, raw))

    def _load_feed_dance_count(self) -> int:
        try:
            raw = int(self.settings.value("feed_dance_count", 0))
        except Exception:
            raw = 0
        return max(0, min(4, raw))

    def _save_feed_dance_count(self):
        self.settings.setValue("feed_dance_count", int(self.feed_dance_count))

    def _complete_feed_can(self):
        self.feed_dance_count = min(5, self.feed_dance_count + 1)
        dance_state = self.state_machine.choose_dance_after_feed(self.feed_dance_count)
        if dance_state is not None:
            self.feed_dance_count = 0
            self._save_feed_dance_count()
            self._enter(dance_state)
            return
        self._save_feed_dance_count()
        self._enter(BaxiState.IDLE)

    def _set_display_scale(self, value: float):
        self.display_scale = max(MIN_DISPLAY_SCALE, min(MAX_DISPLAY_SCALE, value))
        self.settings.setValue("display_scale", self.display_scale)
        self._render_current_frame()
        if self.tray is not None:
            self.tray.setToolTip(f"八喜桌宠 · 大小 {round(self.display_scale * 100)}%")

    def _scale_up(self):
        # Tray formal size adjustment: uniform user scale only.
        self._set_display_scale(self.display_scale + DISPLAY_SCALE_STEP)

    def _scale_down(self):
        # Tray formal size adjustment: uniform user scale only.
        self._set_display_scale(self.display_scale - DISPLAY_SCALE_STEP)

    def _reset_scale(self):
        self._set_display_scale(DEFAULT_DISPLAY_SCALE)

    def _set_size_preset(self, preset: str):
        if preset not in SIZE_PRESETS:
            return
        self._set_display_scale(SIZE_PRESETS[preset])

    def _nearest_size_preset(self) -> str:
        return min(SIZE_PRESETS, key=lambda key: abs(self.display_scale - SIZE_PRESETS[key]))

    def _add_size_adjust_actions(self, menu: QMenu):
        scale_up_action = menu.addAction(f"放大（+{round(DISPLAY_SCALE_STEP * 100)}%）")
        scale_up_action.triggered.connect(self._scale_up)
        scale_down_action = menu.addAction(f"缩小（-{round(DISPLAY_SCALE_STEP * 100)}%）")
        scale_down_action.triggered.connect(self._scale_down)
        return scale_up_action, scale_down_action

    def _add_size_preset_menu(self, menu: QMenu):
        size_menu = menu.addMenu("大小")
        self._add_size_adjust_actions(size_menu)
        size_menu.addSeparator()
        active = self._nearest_size_preset()
        for preset in ("small", "medium", "large"):
            label = SIZE_PRESET_LABELS[preset]
            action = size_menu.addAction(f"{label}（{round(SIZE_PRESETS[preset] * 100)}%）")
            action.setCheckable(True)
            action.setChecked(preset == active)
            action.triggered.connect(lambda checked=False, p=preset: self._set_size_preset(p))
        return size_menu

    def _toggle_diagnostics(self, checked: bool):
        self.diagnostics_enabled = bool(checked)
        self._render_current_frame()

    def _logical_pixmap_for_frame(self, frame):
        source = QPixmap(str(frame.path))
        logical = QPixmap(CANONICAL_CANVAS[0], CANONICAL_CANVAS[1])
        logical.fill(Qt.transparent)
        painter = QPainter(logical)
        offset_x = CANONICAL_FOOT_ANCHOR[0] - frame.foot_anchor[0]
        offset_y = CANONICAL_FOOT_ANCHOR[1] - frame.foot_anchor[1]
        painter.drawPixmap(offset_x, offset_y, source)
        painter.end()
        return logical

    def _commit_logical_pixmap(self, logical):
        rendered_w = max(1, round(CANONICAL_CANVAS[0] * self.display_scale))
        rendered_h = max(1, round(CANONICAL_CANVAS[1] * self.display_scale))
        rendered = logical.scaled(rendered_w, rendered_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._last_rendered_size = rendered.size()
        self.setPixmap(rendered)
        self.resize(rendered.size())

    def _render_current_frame(self):
        if not self.animation.frames:
            return
        safe_frame_index = min(self.frame_index, len(self.animation.frames) - 1)
        frame = self.animation.frames[safe_frame_index]
        logical = self._logical_pixmap_for_frame(frame)
        self._commit_logical_pixmap(logical)
        if self.diagnostics_enabled:
            bbox_w = frame.bbox_xywh[2] * self.display_scale
            bbox_h = frame.bbox_xywh[3] * self.display_scale
            msg = (
                f"state={self.state_machine.state.value} frame={self.frame_index + 1}/{len(self.animation.frames)} "
                f"display_scale={self.display_scale:.2f} source_canvas={self.animation.canvas} "
                f"source_bbox={frame.bbox_xywh} displayed_bbox≈{bbox_w:.1f}x{bbox_h:.1f}"
            )
            self.setToolTip(msg)
            print("[BAXI_DIAG] " + msg, flush=True)
        else:
            self.setToolTip(f"八喜桌宠 · 大小 {round(self.display_scale * 100)}%")

    def _render_transition_frame(self):
        if self._transition_from_frame is None or not self.animation.frames:
            return False
        target_index = min(max(0, getattr(self, "_transition_target_frame_index", 0)), len(self.animation.frames) - 1)
        to_frame = self.animation.frames[target_index]
        total = max(1, self._transition_total_frames)
        progress = min(1.0, (self._transition_frame_index + 1) / total)
        from_logical = self._logical_pixmap_for_frame(self._transition_from_frame)
        to_logical = self._logical_pixmap_for_frame(to_frame)
        logical = QPixmap(CANONICAL_CANVAS[0], CANONICAL_CANVAS[1])
        logical.fill(Qt.transparent)
        painter = QPainter(logical)
        painter.setOpacity(1.0 - progress)
        painter.drawPixmap(0, 0, from_logical)
        painter.setOpacity(progress)
        painter.drawPixmap(0, 0, to_logical)
        painter.end()
        self._commit_logical_pixmap(logical)
        self._transition_frame_index += 1
        if self._transition_frame_index >= total:
            self._transition_from_frame = None
            self._transition_frame_index = 0
            self._transition_total_frames = 0
            self._transition_target_state = None
            target_index = min(max(0, getattr(self, "_transition_target_frame_index", 0)), len(self.animation.frames) - 1)
            self._transition_target_frame_index = 0
            self.frame_index = target_index + 1
            self._restart_timer()
        return True

    def _start_idle_transition(self, from_frame, target_frame_index: int = 0):
        self.animation = self.state_machine.enter(BaxiState.IDLE)
        self.frame_index = 0
        self._transition_from_frame = from_frame
        self._transition_frame_index = 0
        self._transition_total_frames = IDLE_BLEND_FRAMES
        self._transition_target_state = BaxiState.IDLE
        self._transition_target_frame_index = target_frame_index
        self.timer.start(max(1, round(1000 / IDLE_BLEND_FPS)))

    def _start_dance_idle_transition(self, from_frame):
        self._start_idle_transition(from_frame, 0)

    def _start_groom_idle_transition(self, from_frame):
        self._start_idle_transition(from_frame, GROOM_IDLE_TARGET_FRAME_INDEX)

    def next_frame(self):
        if self._transition_from_frame is not None:
            if self._render_transition_frame():
                return
        if not self.animation.frames:
            return
        self._render_current_frame()
        self._advance_walk_position()
        self.frame_index += 1
        if self.frame_index < len(self.animation.frames):
            return
        if self._is_walk_state():
            self._walk_completed_loops += 1
            if self._walk_completed_loops < WALK_LOOP_COUNT:
                self.frame_index = 0
                return
            self.timer.stop()
            QTimer.singleShot(FINAL_HOLD_MS, lambda: self._enter(BaxiState.IDLE))
            return
        if self._is_one_shot():
            completed_state = self.state_machine.state
            final_frame = self.animation.frames[-1]
            self.timer.stop()
            if completed_state is BaxiState.DANCE_01:
                QTimer.singleShot(FINAL_HOLD_MS, lambda f=final_frame: self._start_dance_idle_transition(f))
            elif completed_state is BaxiState.GROOM_PAW:
                QTimer.singleShot(FINAL_HOLD_MS, lambda f=final_frame: self._start_groom_idle_transition(f))
            elif completed_state is BaxiState.FEED_CAN:
                QTimer.singleShot(FINAL_HOLD_MS, self._complete_feed_can)
            else:
                QTimer.singleShot(FINAL_HOLD_MS, lambda s=completed_state: self._enter(self.state_machine.next_after_complete(s)))
            return
        if self.state_machine.state is BaxiState.IDLE:
            next_state = self.state_machine.choose_next_after_idle()
            if next_state is not BaxiState.IDLE:
                self._enter(next_state)
                return
        self.frame_index = 0

    def _try_play(self, state: BaxiState) -> bool:
        try:
            self._enter(state)
        except PendingActionError:
            return False
        return True

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            return
        if event.button() == Qt.RightButton:
            self._open_context_menu(event.globalPosition().toPoint())
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._try_play(BaxiState.GROOM_PAW)
            return
        super().mouseDoubleClickEvent(event)

    def _add_action(self, menu: QMenu, title: str, state: BaxiState):
        action = menu.addAction(title)
        action.setEnabled(not self.state_machine.is_pending(state))
        action.triggered.connect(lambda checked=False, s=state: self._try_play(s))
        return action

    def _populate_formal_actions(self, menu: QMenu):
        # Formal user entry: feed can only. Dance is triggered by feed counter policy.
        self._add_action(menu, "投喂罐头", BaxiState.FEED_CAN)

    def _populate_tray_actions(self, menu: QMenu):
        self._populate_formal_actions(menu)
        menu.addSeparator()
        # Formal tray controls requested for hotfix5: direct zoom in/out.
        self._add_size_adjust_actions(menu)
        menu.addSeparator()
        self._add_size_preset_menu(menu)

    def _open_context_menu(self, global_pos):
        """Formal right-click entry surface: feeding only; dance is feed-triggered."""
        menu = QMenu(self)
        self._populate_formal_actions(menu)
        menu.exec(global_pos)

    def _setup_tray(self):
        if QSystemTrayIcon is None or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        menu = QMenu()
        show_action = menu.addAction("显示八喜")
        show_action.triggered.connect(self.showNormal)
        hide_action = menu.addAction("隐藏八喜")
        hide_action.triggered.connect(self.hide)
        menu.addSeparator()
        self._populate_tray_actions(menu)
        menu.addSeparator()
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(QApplication.instance().quit)

        first_frame = self.animation.frames[0].path if self.animation.frames else None
        icon = QIcon(str(first_frame)) if first_frame else QIcon()
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("八喜桌宠")
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.raise_()
                self.activateWindow()


def main():
    if QApplication is None:
        raise RuntimeError("PySide6 is not installed")
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    w = BaxiPetWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
