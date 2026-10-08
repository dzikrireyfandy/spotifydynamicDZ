# config.py — Visual & app configuration

# === OVERLAY APPEARANCE ===
OVERLAY_WIDTH = 360        # lebih kecil & kompak
OVERLAY_HEIGHT = 44        # lebih ramping
OVERLAY_PADDING_X = 18
OVERLAY_PADDING_Y = 10

# Colors (hex)
BG_COLOR = "#111111"
TEXT_COLOR = "#FFFFFF"
TEXT_DIM_COLOR = "#888888"   # untuk baris sebelumnya / blur
ACCENT_COLOR = "#1DB954"     # Spotify green, buat active line

# Opacity 0.0 - 1.0
BG_OPACITY = 0.88

# Font
FONT_FAMILY = "Segoe UI"
FONT_SIZE_LYRICS = 11
FONT_SIZE_TRACK = 10
FONT_BOLD = True

# Border radius (rounded pill)
BORDER_RADIUS = 32

# === ANIMATION ===
FADE_DURATION_MS = 300       # fade in/out saat lagu ganti
LYRIC_ANIM_MS = 180          # transisi antar baris lirik

# === POLLING ===
TRACK_POLL_INTERVAL_S = 1.5   # deteksi ganti lagu (lebih cepat)
PROGRESS_POLL_INTERVAL_MS = 100  # sync lirik tiap 100ms (hampir realtime)

# === WINDOW POSITION (top-center) ===
# -1 artinya otomatis hitung tengah saat startup
INITIAL_X = -1
INITIAL_Y = 40  # px dari atas layar

# === LYRICS DISPLAY ===
MAX_LYRIC_CHARS = 60         # potong jika terlalu panjang
SHOW_NEXT_LINE = False       # tampilkan 1 baris saja (Dynamic Island style)
