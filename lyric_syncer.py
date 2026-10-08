# lyric_syncer.py — Sync lirik di background thread, update overlay hanya saat baris ganti

import time
import threading
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Plain lyrics: batas waktu per baris (detik)
PLAIN_MIN_S = 2.0   # minimal 2 detik per baris (biar ga terlalu cepet)
PLAIN_MAX_S = 7.0   # maksimal 7 detik per baris (biar ga terlalu lambat)


class LyricSyncer:
    """
    Jalankan di background thread.
    Hitung baris aktif setiap 100ms, tapi hanya panggil callback
    saat baris BENERAN ganti — bukan setiap 100ms.
    """

    def __init__(self, on_line_change: Callable[[str], None]):
        self._on_line_change = on_line_change

        # State lirik
        self._lines: list = []
        self._synced: bool = False
        self._duration_ms: int = 0
        self._lock = threading.Lock()

        # State progress
        self._is_playing: bool = False
        self._last_api_progress: int = 0
        self._last_api_time: float = 0.0

        # State saat ini
        self._current_idx: int = -1
        self._last_line_change_time: float = 0.0  # kapan terakhir ganti baris
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ #
    #  Public API (dipanggil dari thread mana saja)
    # ------------------------------------------------------------------ #

    def set_lyrics(self, lines: list, synced: bool, duration_ms: int):
        """Dipanggil dari LyricsFetcher thread saat lirik selesai di-fetch."""
        with self._lock:
            self._lines = lines
            self._synced = synced
            self._duration_ms = duration_ms
            self._current_idx = -1  # reset biar langsung tampil dari awal

    def update_progress(self, progress_ms: int, is_playing: bool):
        """Dipanggil dari SpotifyPoller thread (tiap 1.5s dari API)."""
        with self._lock:
            self._last_api_progress = progress_ms
            self._last_api_time = time.monotonic()
            self._is_playing = is_playing

    def start(self):
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="LyricSyncer"
        )
        self._thread.start()

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------ #
    #  Internal loop (100ms, background thread)
    # ------------------------------------------------------------------ #

    def _loop(self):
        while self._running:
            self._tick()
            time.sleep(0.1)  # 100ms

    def _tick(self):
        now = time.monotonic()
        with self._lock:
            if not self._is_playing or not self._lines:
                return

            # Estimasi progress sekarang berdasarkan API + waktu berlalu
            elapsed_ms = int((now - self._last_api_time) * 1000)
            estimated_ms = self._last_api_progress + elapsed_ms

            # Hitung idx baris yang aktif
            new_idx = self._find_idx(estimated_ms, now)
            lines_snapshot = self._lines
            synced_snapshot = self._synced

        # Hanya update jika baris berubah
        if new_idx != self._current_idx and new_idx >= 0:
            self._current_idx = new_idx
            self._last_line_change_time = now
            text = lines_snapshot[new_idx].text if new_idx < len(lines_snapshot) else None
            if text:
                self._on_line_change(text)

    def _find_idx(self, progress_ms: int, now: float) -> int:
        """Cari index baris aktif. Dipanggil di dalam lock."""
        if not self._lines:
            return -1

        if self._synced:
            # LRC timestamp mode — ikutin timestamp persis
            idx = 0
            for i, line in enumerate(self._lines):
                if line.time_ms <= progress_ms:
                    idx = i
                else:
                    break
            return idx
        else:
            # Plain lyrics: ratio-based + guard min/max waktu per baris
            if self._duration_ms <= 0:
                return 0

            ratio = min(progress_ms / self._duration_ms, 0.99)
            target_idx = int(ratio * len(self._lines))

            # Jangan ganti baris jika belum lewat PLAIN_MIN_S sejak ganti terakhir
            time_since_last = now - self._last_line_change_time
            if self._current_idx >= 0 and time_since_last < PLAIN_MIN_S:
                return self._current_idx  # tahan dulu

            # Jangan loncat lebih dari 1 baris sekaligus (smooth scroll)
            if self._current_idx >= 0 and target_idx > self._current_idx + 1:
                # Naikkan 1 baris saja kalau sudah lewat minimum
                return self._current_idx + 1

            return target_idx

