# 🎵 Spotify Dynamic Island Lyrics Overlay

Floating lyrics overlay bergaya Dynamic Island untuk Windows. Menampilkan lirik Spotify secara real-time, tersinkronisasi dengan lagu yang sedang diputar.

```
╭──────────────────────────────────────────────╮
│  ● Sparks fly, it's like electricity...      │
╰──────────────────────────────────────────────╯
```

---

## Prasyarat

- Python 3.10+
- Akun Spotify **Premium**
- Akun Spotify Developer (gratis)

---

## Setup (5 menit)

### 1. Install dependencies

```powershell
cd spotify-dynamic-island
pip install -r requirements.txt
```

### 2. Buat Spotify App

1. Buka [https://developer.spotify.com/dashboard/](https://developer.spotify.com/dashboard/)
2. Login dengan akun Spotify kamu
3. Klik **"Create App"**
4. Isi form:
   - **App name**: `Dynamic Island` (bebas)
   - **App description**: apa saja
   - **Redirect URI**: `http://127.0.0.1:8888/callback` ← **WAJIB PERSIS INI**
   - Centang "Web API"
5. Klik **Save**
6. Di halaman app, klik **Settings** → copy `Client ID` dan `Client Secret`

### 3. Buat file .env

```powershell
copy .env.example .env
```

Buka `.env` dengan Notepad dan isi:
```
SPOTIFY_CLIENT_ID=abc123...    ← paste Client ID kamu
SPOTIFY_CLIENT_SECRET=xyz789... ← paste Client Secret kamu
```

### 4. Jalankan!

```powershell
python main.py
```

Browser akan terbuka otomatis untuk login Spotify (hanya sekali). Setelah itu:
- Putar lagu di Spotify
- Overlay Dynamic Island muncul di tengah atas layar 🎉

---

## Cara Pakai

| Aksi | Keterangan |
|------|-----------|
| **Drag** overlay | Pindahkan ke posisi mana saja |
| **Klik kanan** tray icon | Menu Show/Hide & Quit |
| **Double click** tray icon | Show/Hide overlay |

---

## Troubleshooting

**"SPOTIFY_CLIENT_ID harus diisi"**
→ Pastikan file `.env` sudah dibuat dan diisi (bukan `.env.example`)

**Overlay tidak muncul**
→ Pastikan Spotify sedang memutarkan lagu (bukan pause)
→ Pastikan akun Spotify Premium aktif

**Lirik tidak muncul**
→ Beberapa lagu tidak memiliki lirik di database LRCLIB
→ Overlay tetap muncul menampilkan nama lagu & artis

**Browser tidak terbuka saat login**
→ Jalankan dari PowerShell (bukan dari IDE)
→ Copy URL yang muncul di terminal, paste ke browser manual

---

## Struktur File

```
spotify-dynamic-island/
├── main.py              # Entry point
├── spotify_poller.py    # Ambil data dari Spotify API
├── lyrics_engine.py     # Fetch & parse lirik dari LRCLIB
├── overlay_widget.py    # GUI Dynamic Island (PyQt6)
├── config.py            # Konfigurasi visual & polling
├── requirements.txt
└── .env                 # Credentials (JANGAN share ke orang lain!)
```
