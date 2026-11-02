# 🎬 AI Shorts Studio Bot (`apps/ai-video-generator-bot`)

> 🤖 **Telegram Bot**: [@aivideogenerator2004_bot](https://t.me/aivideogenerator2004_bot)  
> 🟢 **Status**: Built & Ready (Long Polling & Daily Automation Scheduler)

An automated, end-to-end **AI YouTube Shorts / Faceless Video Creator Bot** built with **Python 3.13**, **`aiogram v3`**, **Google Gemini**, **Edge-TTS**, **Pollinations FLUX**, and **MoviePy / FFmpeg**.

Produces high-retention, vertical **9:16 (1080x1920)** videos complete with cinematic imagery, smooth Ken Burns zoom effects, viral hooks, word-by-word kinetic highlighted subtitles, background music mixing, and optional YouTube Data API v3 upload.

---

## ⚡ Key Highlights & Features

- **🧠 Viral Scripting Engine (Google Gemini)**: Generates high-CTR titles, 3-second psychological hooks, 5-7 punchy scenes, and SEO tags optimized for Shorts algorithms.
- **🎙️ Neural Spoken Audio (Edge-TTS)**: Studio-grade global English voiceover (`en-US-ChristopherNeural` / `en-US-JennyNeural`) with exact microsecond word-level boundaries for kinetic subtitle timing.
- **🎨 AI Visual Pipeline (Pollinations FLUX)**: Fetches photorealistic 8K vertical imagery without requiring paid API keys, with automatic Pexels B-roll and stylized gradient canvas fallback.
- **🎞️ Compositor & Kinetic Subtitles (MoviePy + FFmpeg + Pillow)**:
  - 1080x1920 @ 30fps vertical composition.
  - Alternating Ken Burns pan/zoom effects on every scene.
  - Word-by-word highlighted kinetic captions (Alex Hormozi / CapCut style) rendered cleanly without ImageMagick dependencies.
  - Background music (BGM) mixing with -18dB audio ducking.
- **⏰ Daily Automated Cron Scheduler (APScheduler)**: Automatically creates and drops at least 1 fresh Shorts video every day at `08:00 WIB` directly to your Telegram chat.
- **📱 Interactive Telegram Bot UI**: Inline buttons for topic selection, on-demand `/generate`, latency diagnostic `/status`, and direct `.mp4` preview.
- **🚀 YouTube Data API v3 Integration**: One-click or auto-upload to your YouTube Shorts channel.
- **💾 Embedded SQLite Persistence**: Asynchronously stores video history, user activity, and generation logs using `aiosqlite`.

---

## 🏛️ Pipeline Architecture

```
[ Trigger: Daily Cron (08:00 WIB) OR Telegram Command /generate ]
                             │
                             ▼
              [ Gemini 2.5 / 3.1 Flash LLM ]
              (Hook, Scenes, & Visual Prompts)
                 /                       \
                ▼                         ▼
      [ Edge-TTS Synthesis ]    [ Pollinations.ai (FLUX) ]
   (Voiceover + Word Timestamps) (1080x1920 Scene Visuals)
                \                         /
                 ▼                       ▼
            [ MoviePy + FFmpeg Video Compositor ]
            - Ken Burns Pan / Zoom Effect
            - Kinetic Word-by-Word Subtitles
            - Background Music (BGM Ducking)
                             │
                             ▼
          [ Final Rendered 1080x1920 .mp4 ]
                 /                       \
                ▼                         ▼
   [ Telegram Video Delivery ]   [ Optional: YouTube Shorts Upload ]
```

---

## 🗂️ Project Directory Structure

```text
apps/ai-video-generator-bot/
├── api/
│   └── webhook.py            # ⚡ Vercel Serverless Webhook Bridge (<200ms)
├── assets/
│   ├── bgm/                  # Royalty-free background music tracks
│   ├── characters/siesta/    # 17 Emotion Sprite expressions
│   └── fonts/                # Bold typography for subtitles
├── scripts/
│   └── run_production_pipeline.py # Production CLI & GitHub Actions runner
├── src/
│   ├── bot/
│   │   ├── handlers/         # base.py (/start, /status, /stats), generator.py (/generate, /topics)
│   │   ├── keyboards/        # Interactive inline & reply keyboards
│   │   └── middleware/       # User tracking middleware
│   ├── services/
│   │   ├── script_gen.py     # Gemini structured script & 15+ category generator
│   │   ├── voice_service.py  # Edge-TTS neural speech & timestamp extractor
│   │   ├── image_service.py  # 4-tier visual resilience pipeline
│   │   ├── avatar_service.py # Siesta animated avatar compositor
│   │   ├── thumbnail_service.py # High-CTR 9:16 vertical thumbnail generator
│   │   ├── video_engine.py   # MoviePy compositor, Ken Burns, subtitles
│   │   ├── video_orchestrator.py # Master pipeline orchestrator
│   │   ├── scheduler.py      # APScheduler daily automation
│   │   └── youtube_service.py# YouTube Data API v3 uploader
│   ├── repositories/
│   │   ├── database.py       # aiosqlite schema initialization (WAL mode)
│   │   └── video_repo.py     # Video & user persistence
│   └── config.py             # Pydantic Settings
├── storage/
│   ├── temp/                 # Temporary render files (auto-purged)
│   └── output/               # Rendered final .mp4 videos
├── tests/                    # 10/10 Comprehensive unit & e2e render tests
├── main.py                   # Local development bot runner & polling
├── vercel.json               # Vercel serverless routing configuration
├── Dockerfile                # Docker container with FFmpeg
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Setup Virtual Environment
```bash
cd apps/ai-video-generator-bot
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Credentials in `.env`
Salin template konfigurasi dan masukkan token bot Anda:
```env
BOT_TOKEN=your_telegram_bot_token_from_botfather
GEMINI_API_KEY=your_gemini_api_key
TARGET_CHAT_ID=your_telegram_chat_id
DAILY_SCHEDULE_TIME="08:00"
SCHEDULER_TIMEZONE="Asia/Jakarta"
```

### 4. Run Automated Test Suite (10/10 Tests)
```bash
pytest -v
```

### 5. Launch Local Development Bot (Polling Mode)
```bash
python main.py
```

### 6. Production Mode (100% Gratis: GitHub Actions + Vercel Webhook)

Arsitektur production dirancang khusus untuk mengatasi batas waktu serverless (Vercel max 10s-60s) dengan membagi tugas secara optimal:
- **Telegram Webhook Bridge (Vercel)**: Menerima perintah Telegram (`/generate`, `/status`) dan merespons dalam <200ms.
- **Render Engine (GitHub Actions)**: Menjalankan MoviePy + FFmpeg pada runner 4 vCPU & 16 GB RAM (gratis 2.000 menit/bulan), mengunggah ke YouTube Shorts, dan mengirim video `.mp4` ke Telegram Anda.

#### A. Konfigurasi GitHub Repository Secrets
Buka repository GitHub Anda -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**:

| Secret Name | Deskripsi |
| :--- | :--- |
| `BOT_TOKEN` | Token bot Telegram dari @BotFather |
| `TARGET_CHAT_ID` | ID akun/channel Telegram Anda (misal: `7741750167`) |
| `GEMINI_API_KEY` | API Key dari Google AI Studio |
| `PEXELS_API_KEY` | API Key Pexels (opsional untuk B-roll visual) |
| `YOUTUBE_TOKEN_JSON` | Salin seluruh teks dari file `youtube_token.json` |

#### B. Konfigurasi Vercel Webhook Bridge
1. Deploy folder `apps/ai-video-generator-bot` ke **Vercel**.
2. Tambahkan **Environment Variables** di dashboard project Vercel:
   - `BOT_TOKEN`: Token bot Telegram Anda
   - `TARGET_CHAT_ID`: ID akun Telegram Anda (hanya chat ini yang diizinkan trigger render)
   - `GH_PAT`: GitHub Personal Access Token (dengan scope `repo` untuk memicu dispatch)
   - `GITHUB_REPOSITORY`: `Username/RepositoryName` (contoh: `TinoNurcahya/telegram-bots`)
3. Daftarkan Webhook Telegram ke Vercel:
   ```bash
   curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<your-vercel-domain>.vercel.app/api/webhook"
   ```

#### C. Menjalankan Pipeline Secara Manual / CLI
Untuk membuat video langsung dari command line tanpa Telegram:
```bash
# Topik acak dari 15+ kategori misteri & sains:
python scripts/run_production_pipeline.py --trigger manual

# Dengan topik kustom tertentu:
python scripts/run_production_pipeline.py --topic "Rahasia Bawah Tanah Svalbard Seed Vault" --trigger manual
```

---

## 🎮 Command Reference

| Command | Action |
| :--- | :--- |
| `/start` | Membuka menu interaktif studio video |
| `/generate [topik]` | Memulai produksi video Shorts AI secara instan sesuai topik yang diinginkan |
| `/topics` | Menampilkan ide topik viral trending yang siap digenerate |
| `/status` | Menampilkan round-trip ping latency, resolusi, dan status scheduler harian |
| `/stats` | Menampilkan total video yang telah digenerate dan riwayat render |
| `/help` | Menampilkan panduan lengkap penggunaan |

---

## 📄 License

Proprietary portfolio license. Part of the **Telegram Bots Monorepo Portfolio Showcase**.
