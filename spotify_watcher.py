# spotify_watcher.py — Monitor proses Spotify, auto launch/kill overlay

import subprocess
import sys
import time
import logging
import threading

logger = logging.getLogger(__name__)

SPOTIFY_PROCESS_NAMES = ["Spotify.exe", "spotify.exe"]
CHECK_INTERVAL_S = 3.0  # cek setiap 3 detik


def is_spotify_running() -> bool:
    """Cek apakah Spotify sedang berjalan."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Spotify.exe", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        return "Spotify.exe" in result.stdout
    except Exception:
        return False


def watch_and_launch():
    """
    Loop utama:
    - Tunggu sampai Spotify terbuka
    - Launch overlay
    - Tunggu sampai Spotify ditutup
    - Kill overlay
    - Ulangi
    """
    overlay_process = None
    was_running = False

    print("Menunggu Spotify dibuka...")

    while True:
        running = is_spotify_running()

        if running and not was_running:
            # Spotify baru dibuka → launch overlay
            print("Spotify terdeteksi! Meluncurkan overlay...")
            overlay_process = subprocess.Popen(
                [sys.executable, "main.py"],
                creationflags=subprocess.CREATE_NO_WINDOW  # tanpa console window
            )
            was_running = True

        elif not running and was_running:
            # Spotify ditutup → matikan overlay
            print("Spotify ditutup. Mematikan overlay...")
            if overlay_process and overlay_process.poll() is None:
                overlay_process.terminate()
                overlay_process = None
            was_running = False
            print("Menunggu Spotify dibuka lagi...")

        time.sleep(CHECK_INTERVAL_S)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        watch_and_launch()
    except KeyboardInterrupt:
        print("\nWatcher dihentikan.")
