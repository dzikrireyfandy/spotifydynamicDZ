# lyrics_engine.py — Fetch & parse synced lyrics, dengan multi-source fallback

import requests
import re
import time
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

LRCLIB_SEARCH_URL = "https://lrclib.net/api/search"
LRCLIB_GET_URL = "https://lrclib.net/api/get"


@dataclass
class LyricLine:
    time_ms: int      # 0 untuk plain lyrics
    text: str


class LyricsEngine:
    def __init__(self):
        self._cache: dict[str, list[LyricLine]] = {}
        self._is_synced: dict[str, bool] = {}

    def _key(self, track: str, artist: str) -> str:
        return f"{artist.lower().strip()}::{track.lower().strip()}"

    def fetch(self, track_name: str, artist_name: str,
              album_name: str = "", duration_s: int = 0) -> Optional[list[LyricLine]]:
        """
        Fetch lyrics dengan fallback:
        1. LRCLIB synced (LRC format) — paling akurat
        2. LRCLIB search (cari by keyword) — kalau exact match gagal
        3. LRCLIB plain lyrics — scroll otomatis tiap beberapa detik
        """
        key = self._key(track_name, artist_name)
        if key in self._cache:
            return self._cache[key]

        # === Attempt 1: LRCLIB exact match ===
        lines, synced = self._lrclib_get(track_name, artist_name, album_name, duration_s)

        # === Attempt 2: LRCLIB search (lebih fleksibel) ===
        if lines is None:
            logger.info(f"Exact match gagal, coba search LRCLIB...")
            lines, synced = self._lrclib_search(track_name, artist_name)

        if lines is None:
            lines = []
            synced = False

        self._cache[key] = lines
        self._is_synced[key] = synced

        if lines:
            mode = "synced" if synced else "plain (auto-scroll)"
            logger.info(f"Lyrics ready [{mode}]: {len(lines)} lines — {artist_name} - {track_name}")
        else:
            logger.warning(f"Tidak ada lyrics untuk: {artist_name} - {track_name}")

        return lines

    def is_synced(self, track_name: str, artist_name: str) -> bool:
        key = self._key(track_name, artist_name)
        return self._is_synced.get(key, False)

    def get_current_line(self, lines: list[LyricLine], progress_ms: int,
                         synced: bool, duration_ms: int = 0) -> tuple[int, str]:
        """
        Cari baris aktif:
        - Jika synced: pakai timestamp LRC
        - Jika plain: bagi durasi rata per baris (auto-scroll)
        """
        if not lines:
            return -1, ""

        if synced:
            current_idx = 0
            for i, line in enumerate(lines):
                if line.time_ms <= progress_ms:
                    current_idx = i
                else:
                    break
            return current_idx, lines[current_idx].text
        else:
            # Plain lyrics: estimasi posisi berdasarkan durasi
            if duration_ms <= 0:
                return 0, lines[0].text
            ratio = progress_ms / duration_ms
            idx = min(int(ratio * len(lines)), len(lines) - 1)
            return idx, lines[idx].text

    # ------------------------------------------------------------------ #
    #  LRCLIB methods
    # ------------------------------------------------------------------ #

    def _lrclib_get(self, track_name, artist_name, album_name="", duration_s=0):
        """Exact match ke LRCLIB."""
        params = {"artist_name": artist_name, "track_name": track_name}
        if album_name:
            params["album_name"] = album_name
        if duration_s:
            params["duration"] = duration_s
        try:
            r = requests.get(LRCLIB_GET_URL, params=params, timeout=8)
            if r.status_code == 404:
                return None, False
            r.raise_for_status()
            return self._extract_from_response(r.json())
        except Exception as e:
            logger.error(f"LRCLIB get error: {e}")
            return None, False

    def _lrclib_search(self, track_name, artist_name):
        """Search LRCLIB — lebih toleran terhadap perbedaan nama."""
        try:
            r = requests.get(
                LRCLIB_SEARCH_URL,
                params={"q": f"{artist_name} {track_name}"},
                timeout=8
            )
            r.raise_for_status()
            results = r.json()
            if not results:
                return None, False
            # Ambil hasil pertama
            return self._extract_from_response(results[0])
        except Exception as e:
            logger.error(f"LRCLIB search error: {e}")
            return None, False

    def _extract_from_response(self, data: dict):
        """Ekstrak synced atau plain lyrics dari response LRCLIB."""
        synced_lrc = data.get("syncedLyrics") or ""
        plain_text = data.get("plainLyrics") or ""

        if synced_lrc:
            lines = self._parse_lrc(synced_lrc)
            if lines:
                return lines, True

        if plain_text:
            lines = self._parse_plain(plain_text)
            if lines:
                return lines, False

        return None, False

    def _parse_lrc(self, lrc_text: str) -> list[LyricLine]:
        """Parse format LRC: [mm:ss.xx] text"""
        pattern = re.compile(r"\[(\d{2}):(\d{2})[\.\:](\d{2,3})\](.*)")
        lines = []
        for raw in lrc_text.splitlines():
            m = pattern.match(raw.strip())
            if not m:
                continue
            mm, ss = int(m.group(1)), int(m.group(2))
            cs = m.group(3)
            ms = int(cs) * 10 if len(cs) == 2 else int(cs)
            time_ms = (mm * 60 + ss) * 1000 + ms
            text = m.group(4).strip()
            if text:
                lines.append(LyricLine(time_ms=time_ms, text=text))
        return sorted(lines, key=lambda l: l.time_ms)

    def _parse_plain(self, plain_text: str) -> list[LyricLine]:
        """Parse plain lyrics — semua baris jadi LyricLine dengan time_ms=0."""
        lines = []
        for line in plain_text.splitlines():
            text = line.strip()
            if text:
                lines.append(LyricLine(time_ms=0, text=text))
        return lines

    def clear_cache(self):
        self._cache.clear()
        self._is_synced.clear()
