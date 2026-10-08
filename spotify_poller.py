# spotify_poller.py — Poll Spotify API untuk track & progress

import os
import time
import threading
import logging
from dataclasses import dataclass
from typing import Optional, Callable

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SCOPES = "user-read-currently-playing user-read-playback-state"


@dataclass
class TrackInfo:
    track_id: str
    track_name: str
    artist_name: str
    album_name: str
    duration_ms: int
    progress_ms: int
    is_playing: bool


class SpotifyPoller:
    def __init__(
        self,
        on_track_change: Callable[[Optional[TrackInfo]], None],
        on_progress_update: Callable[[int, bool], None],
        track_interval_s: float = 3.0,
        progress_interval_ms: int = 500,
    ):
        """
        on_track_change   : dipanggil saat lagu berganti atau mulai/stop
        on_progress_update: dipanggil setiap progress_interval_ms (progress_ms, is_playing)
        """
        self._on_track_change = on_track_change
        self._on_progress_update = on_progress_update
        self._track_interval = track_interval_s
        self._progress_interval = progress_interval_ms / 1000.0

        self._sp: Optional[spotipy.Spotify] = None
        self._current_track_id: Optional[str] = None
        self._current_progress_ms: int = 0
        self._is_playing: bool = False
        self._last_progress_fetch: float = 0.0

        self._stop_event = threading.Event()
        self._track_thread: Optional[threading.Thread] = None
        self._progress_thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        """Inisialisasi Spotipy OAuth. Buka browser jika belum login."""
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

        if not client_id or not client_secret:
            raise ValueError(
                "SPOTIFY_CLIENT_ID dan SPOTIFY_CLIENT_SECRET harus diisi di file .env!\n"
                "Buat app di: https://developer.spotify.com/dashboard/"
            )

        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=SCOPES,
            cache_path=".spotify_token_cache",
            open_browser=True,
        )

        self._sp = spotipy.Spotify(auth_manager=auth_manager)
        logger.info("Spotify connected ✓")
        return True

    def start(self):
        """Mulai background threads untuk polling."""
        self._stop_event.clear()

        self._track_thread = threading.Thread(
            target=self._track_loop, daemon=True, name="SpotifyTrackPoller"
        )
        self._progress_thread = threading.Thread(
            target=self._progress_loop, daemon=True, name="SpotifyProgressPoller"
        )
        self._track_thread.start()
        self._progress_thread.start()
        logger.info("Spotify pollers started")

    def stop(self):
        """Hentikan polling."""
        self._stop_event.set()

    # ------------------------------------------------------------------ #
    #  Internal loops
    # ------------------------------------------------------------------ #

    def _track_loop(self):
        """Poll pergantian lagu setiap beberapa detik."""
        while not self._stop_event.is_set():
            try:
                self._fetch_track()
            except Exception as e:
                logger.error(f"Track poll error: {e}")
            self._stop_event.wait(self._track_interval)

    def _progress_loop(self):
        """Update progress tiap 100ms menggunakan estimasi lokal (tanpa API call)."""
        while not self._stop_event.is_set():
            try:
                if self._is_playing and self._last_progress_fetch > 0:
                    # Interpolasi lokal: progress_api + waktu_berlalu sejak fetch terakhir
                    elapsed_ms = int((time.monotonic() - self._last_progress_fetch) * 1000)
                    estimated = self._current_progress_ms + elapsed_ms
                    self._on_progress_update(estimated, True)
                elif not self._is_playing:
                    self._on_progress_update(self._current_progress_ms, False)
            except Exception as e:
                logger.error(f"Progress update error: {e}")
            self._stop_event.wait(self._progress_interval)


    def _fetch_track(self):
        """Ambil info track dari Spotify API."""
        try:
            result = self._sp.currently_playing()
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Spotify API error: {e}")
            return

        if not result or not result.get("item"):
            # Tidak ada yang diputar
            if self._current_track_id is not None:
                self._current_track_id = None
                self._is_playing = False
                self._on_track_change(None)
            return

        item = result["item"]
        track_id = item["id"]
        is_playing = result.get("is_playing", False)
        progress_ms = result.get("progress_ms", 0)

        # Sinkronkan progress dari API (bukan estimasi)
        self._current_progress_ms = progress_ms
        self._is_playing = is_playing
        self._last_progress_fetch = time.monotonic()

        # Cek apakah lagu berubah
        if track_id != self._current_track_id:
            self._current_track_id = track_id
            artists = ", ".join(a["name"] for a in item.get("artists", []))
            album = item.get("album", {}).get("name", "")
            duration_ms = item.get("duration_ms", 0)

            info = TrackInfo(
                track_id=track_id,
                track_name=item["name"],
                artist_name=artists,
                album_name=album,
                duration_ms=duration_ms,
                progress_ms=progress_ms,
                is_playing=is_playing,
            )
            logger.info(f"Track changed → {artists} — {item['name']}")
            self._on_track_change(info)

        # Update playing state
        self._on_progress_update(progress_ms, is_playing)
