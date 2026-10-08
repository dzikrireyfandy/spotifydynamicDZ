# main.py — Entry point Spotify Dynamic Island Lyrics Overlay

import sys
import logging
import threading
from typing import Optional

from PyQt6.QtWidgets import QApplication

from config import TRACK_POLL_INTERVAL_S, PROGRESS_POLL_INTERVAL_MS
from spotify_poller import SpotifyPoller, TrackInfo
from lyrics_engine import LyricsEngine
from lyric_syncer import LyricSyncer
from overlay_widget import DynamicIslandOverlay

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class SpotifyDynamicIsland:
    def __init__(self, app: QApplication, overlay: DynamicIslandOverlay):
        self._overlay = overlay
        self._lyrics = LyricsEngine()
        self._current_track: Optional[TrackInfo] = None

        # LyricSyncer: hitung baris aktif di background, callback hanya saat ganti
        self._syncer = LyricSyncer(
            on_line_change=self._on_lyric_line_changed
        )

        self._poller = SpotifyPoller(
            on_track_change=self._on_track_change,
            on_progress_update=self._on_progress_update,
            track_interval_s=TRACK_POLL_INTERVAL_S,
            progress_interval_ms=PROGRESS_POLL_INTERVAL_MS,
        )

    def start(self):
        logger.info("Connecting to Spotify...")
        self._poller.connect()
        self._syncer.start()
        self._poller.start()
        logger.info("Dynamic Island started!")

    def stop(self):
        self._poller.stop()
        self._syncer.stop()

    # ------------------------------------------------------------------ #
    #  Callbacks
    # ------------------------------------------------------------------ #

    def _on_track_change(self, track_info: Optional[TrackInfo]):
        """Lagu berganti — reset syncer, fetch lirik baru."""
        self._current_track = track_info

        # Reset syncer
        self._syncer.set_lyrics([], synced=False, duration_ms=0)

        # Notify overlay (thread-safe)
        self._overlay.notify_track_changed(track_info)
        self._overlay.notify_playing_state(track_info.is_playing if track_info else False)

        if track_info is None:
            return

        threading.Thread(
            target=self._fetch_lyrics,
            args=(track_info,),
            daemon=True,
            name="LyricsFetcher",
        ).start()

    def _on_progress_update(self, progress_ms: int, is_playing: bool):
        """Progress dari API → update syncer (bukan langsung ke overlay)."""
        self._syncer.update_progress(progress_ms, is_playing)

    def _on_lyric_line_changed(self, text: str):
        """
        Dipanggil LyricSyncer HANYA saat baris ganti.
        Ini dari background thread → pakai signal Qt yang thread-safe.
        """
        self._overlay.notify_lyric_changed(text)

    def _fetch_lyrics(self, track_info: TrackInfo):
        """Background thread: fetch & parse lirik."""
        logger.info(f"Fetching lyrics: {track_info.artist_name} - {track_info.track_name}")

        lines = self._lyrics.fetch(
            track_name=track_info.track_name,
            artist_name=track_info.artist_name,
            album_name=track_info.album_name,
            duration_s=track_info.duration_ms // 1000,
        )

        # Pastikan track masih sama
        if not (self._current_track and self._current_track.track_id == track_info.track_id):
            return

        if lines:
            synced = self._lyrics.is_synced(track_info.track_name, track_info.artist_name)
            self._syncer.set_lyrics(lines, synced=synced, duration_ms=track_info.duration_ms)
            mode = "SYNCED" if synced else "plain (auto-scroll)"
            logger.info(f"Lyrics loaded [{mode}]: {len(lines)} lines")
        else:
            logger.info("Tidak ada lirik tersedia untuk lagu ini")


def main():
    print("=" * 50)
    print("  Spotify Dynamic Island Lyrics Overlay")
    print("=" * 50)
    print()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    overlay = DynamicIslandOverlay(app)
    controller = SpotifyDynamicIsland(app, overlay)

    try:
        controller.start()
    except ValueError as e:
        print(f"\nERROR: {e}\n")
        print("Pastikan file .env sudah diisi dengan benar.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}\n")
        sys.exit(1)

    print("\nOverlay aktif! Putar lagu di Spotify.")
    print("  Klik kanan tray icon untuk menutup")
    print("  Drag overlay untuk memindah posisi\n")

    exit_code = app.exec()
    controller.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
