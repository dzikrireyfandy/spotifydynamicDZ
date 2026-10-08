# overlay_widget.py — Dynamic Island GUI using PyQt6

import logging
from typing import Optional

from PyQt6.QtWidgets import QWidget, QApplication, QSystemTrayIcon, QMenu, QStyle
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QBrush, QPen, QPainterPath, QAction

import config

logger = logging.getLogger(__name__)


class DynamicIslandOverlay(QWidget):
    """
    Floating pill-shaped overlay bergaya Dynamic Island.
    Posisi: tengah atas, bisa di-drag.
    """

    # Signal dari background thread → main thread (Qt-safe)
    _sig_track_changed = pyqtSignal(object)   # TrackInfo | None
    _sig_lyric_changed = pyqtSignal(str)       # teks baris baru (hanya saat ganti)
    _sig_playing_state = pyqtSignal(bool)      # is_playing

    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app

        # State
        self._current_lyric = ""
        self._is_playing = False

        # Animation
        self._opacity_val: float = 0.0
        self._target_height = config.OVERLAY_HEIGHT
        self._current_height = 0

        # Drag
        self._drag_pos: Optional[QPoint] = None

        self._sig_track_changed.connect(self._handle_track_changed)
        self._sig_lyric_changed.connect(self._handle_lyric_changed)
        self._sig_playing_state.connect(self._handle_playing_state)

        self._setup_window()
        self._setup_tray()
        self._setup_anim_timer()

    # ------------------------------------------------------------------ #
    #  Window setup
    # ------------------------------------------------------------------ #

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        screen = self._app.primaryScreen().geometry()
        x = (screen.width() - config.OVERLAY_WIDTH) // 2
        self.setGeometry(x, config.INITIAL_Y, config.OVERLAY_WIDTH, config.OVERLAY_HEIGHT)
        self.hide()

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self._app.style().standardIcon(
            QStyle.StandardPixmap.SP_MediaPlay
        ))
        self._tray.setToolTip("Spotify Dynamic Island")

        menu = QMenu()
        show_act = QAction("Show/Hide", self)
        show_act.triggered.connect(self._toggle_visibility)
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(self._app.quit)
        menu.addAction(show_act)
        menu.addSeparator()
        menu.addAction(quit_act)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _setup_anim_timer(self):
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60fps
        self._anim_timer.timeout.connect(self._animate_step)

    # ------------------------------------------------------------------ #
    #  Public — dipanggil dari background thread (thread-safe via signal)
    # ------------------------------------------------------------------ #

    def notify_track_changed(self, track_info):
        self._sig_track_changed.emit(track_info)

    def notify_lyric_changed(self, text: str):
        self._sig_lyric_changed.emit(text)

    def notify_playing_state(self, is_playing: bool):
        self._sig_playing_state.emit(is_playing)

    # ------------------------------------------------------------------ #
    #  Slots — dijalankan di main thread
    # ------------------------------------------------------------------ #

    def _handle_track_changed(self, track_info):
        if track_info is None:
            self._collapse()
        else:
            # Tampilkan nama lagu sementara lirik di-fetch
            self._current_lyric = f"{track_info.artist_name} — {track_info.track_name}"
            self.update()
            self._expand()

    def _handle_lyric_changed(self, text: str):
        """Hanya dipanggil saat baris lirik BENERAN ganti."""
        self._current_lyric = text
        self.update()

    def _handle_playing_state(self, is_playing: bool):
        if not is_playing:
            self._collapse()
        else:
            self._expand()

    # ------------------------------------------------------------------ #
    #  Animation
    # ------------------------------------------------------------------ #

    def _expand(self):
        self.show()
        self._target_height = config.OVERLAY_HEIGHT
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _collapse(self):
        self._target_height = 0
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _animate_step(self):
        speed = 4
        if self._current_height < self._target_height:
            self._current_height = min(self._current_height + speed, self._target_height)
        elif self._current_height > self._target_height:
            self._current_height = max(self._current_height - speed, self._target_height)
        else:
            self._anim_timer.stop()
            if self._target_height == 0:
                self.hide()
            return

        self._opacity_val = self._current_height / config.OVERLAY_HEIGHT
        self.setFixedHeight(max(1, self._current_height))
        self.update()

    # ------------------------------------------------------------------ #
    #  Paint
    # ------------------------------------------------------------------ #

    def paintEvent(self, event):
        if self._current_height <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self._current_height

        # Background pill hitam
        bg = QColor(config.BG_COLOR)
        bg.setAlphaF(config.BG_OPACITY * self._opacity_val)
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, config.BORDER_RADIUS, config.BORDER_RADIUS)
        painter.fillPath(path, QBrush(bg))

        if self._opacity_val < 0.3:
            painter.end()
            return

        # Dot hijau Spotify
        dot_color = QColor(config.ACCENT_COLOR)
        dot_color.setAlphaF(self._opacity_val)
        painter.setBrush(QBrush(dot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        dot_size = 7
        dot_x = config.OVERLAY_PADDING_X
        dot_y = (h - dot_size) // 2
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

        # Teks lirik
        text_color = QColor(config.TEXT_COLOR)
        text_color.setAlphaF(self._opacity_val)
        painter.setPen(QPen(text_color))

        font = QFont(config.FONT_FAMILY, config.FONT_SIZE_LYRICS)
        font.setBold(config.FONT_BOLD)
        painter.setFont(font)

        text_x = dot_x + dot_size + 8
        painter.drawText(
            text_x, 0, w - text_x - config.OVERLAY_PADDING_X, h,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._current_lyric
        )
        painter.end()

    # ------------------------------------------------------------------ #
    #  Drag
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_visibility()
