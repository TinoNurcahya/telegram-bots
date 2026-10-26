# AI English Speaking Coach Bot 🎙️

[![Telegram Bot](https://img.shields.io/badge/Telegram_Bot-@MyEnglishCoach2000__bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/MyEnglishCoach2000_bot)
[![Vercel Deployment](https://img.shields.io/badge/Vercel_Serverless-Live-black?style=for-the-badge&logo=vercel)](https://speaking-coach-bot.tinonurcahya.dev/api/index)
[![Tests Passing](https://img.shields.io/badge/Tests-77%2F77_Passing-brightgreen?style=for-the-badge)](tests/)

> 🤖 **Coba Langsung di Telegram:** [@MyEnglishCoach2000_bot](https://t.me/MyEnglishCoach2000_bot)  
> 🌐 **Live Webhook Endpoint:** [speaking-coach-bot.tinonurcahya.dev](https://speaking-coach-bot.tinonurcahya.dev/api/index)

An interactive, AI-powered English Speaking Coach Telegram Bot built with **Python 3.13**, **aiogram v3**, **Google Gemini 3.1 Flash-Lite Multimodal Audio**, and **Neural Text-to-Speech (`edge-tts`)**, structured with enterprise **Clean Architecture**.

Learners simply hold down the Telegram microphone button (🎙️), speak in English, and receive:
1. 📝 **Comprehensive Analysis**: Transcription, CEFR level, IELTS band estimation, grammar slip fixes, vocabulary upgrades, and pronunciation notes.
2. 🔊 **Spoken Voice Note Reply**: The AI speaks back naturally with a realistic neural voice note in native US/UK accents!

---

## ✨ Features

- **Direct Voice Note Ingestion**: Processes Telegram `.oga` / `.ogg` voice notes natively via Google Gemini's audio model with zero FFmpeg transcode overhead.
- **🎓 Official 3-Part IELTS Mock Exam (`/mock_ielts`)**: Full simulation of official British Council / IDP speaking interviews:
  - *Part 1*: Familiar interview via *blind listening* spoken examiner voice notes.
  - *Part 2*: Cue Card task with interactive 60-second preparation countdown & monologue recording.
  - *Part 3*: In-depth two-way analytical discussion.
  - *Official Scorecard*: Full assessment of Fluency & Coherence (FC), Lexical Resource (LR), Grammatical Range & Accuracy (GRA), and Pronunciation (PR) with Overall Band Score (0.0–9.0) and `+100 XP` reward!
- **🎧 Native Shadowing Mode (`/shadow`)**: Bot plays a native audio sentence; you repeat/shadow it, and AI computes your pronunciation match accuracy (0-100%), rhythm, and mispronounced words.
- **👄 Phonetics Clinic & Minimal Pairs (`/phonemes`)**: Correct chronic pronunciation blindspots (e.g. `/θ/ vs /s/`, `/v/ vs /b/`, `/l/ vs /r/`, `/ʃ/ vs /s/`, `/æ/ vs /e/`, `/p/ vs /f/`) with on-demand audio playback, acoustic IPA diffing, physical mouth/tongue guides, and `+25 XP` rewards!
- **🔥 Daily Practice Streak Engine (`/progress`)**: Tracks consecutive days of practice, preserves record streaks, and awards bonus XP (`+15 XP` per voice note, `+25 XP` streak bonus, `+100 XP` for mock exam).
- **⏰ Proactive Duolingo-Style Daily Reminders (`/remind`)**: Background worker that checks in daily with entertaining, dynamic persona variations to ensure streaks never break!
- **🔊 Neural Voice Note Replies**: Uses async `edge-tts` to generate natural native voice replies directly in Telegram chat (Zero API keys required for audio playback).
- **🎭 Roleplay Scenarios (`/scenario`)**:
  - 💼 *Job Interview Simulation* (Behavioral & technical questions)
  - ☕ *Cafe & Dining* (Ordering food and casual talk)
  - ✈️ *Airport & Immigration* (Border control & travel questions)
  - 🏢 *Tech Team Daily Standup* (Agile work updates & blockers)
  - 🗣️ *Free Casual Conversation* (Everyday passions & cultural exchange)
- **📊 CEFR & IELTS Band Estimation**: Provides quantitative ratings (A1–C2, IELTS 4.0–8.5) based on fluency, grammatical range, and lexical resource.
- **📖 Weak-Word & Grammar Bank (`/review`)**: Automatically logs any grammar slips and awkward phrases to SQLite so learners can review them anytime.
- **🎙️ Customizable Voice Accents (`/voice`)**: Switch between US (Jenny/Guy) and UK (Sonia/Ryan) neural voices.
- **🎯 Adaptive Difficulty Levels (`/level`)**: Beginner (A1-A2), Intermediate (B1-B2), Advanced (C1-C2).
- **💡 Daily Topic Generator (`/topic`)**: Generates fresh conversation starters on demand.
- **⚡ Asynchronous Queue-Worker (`arq` + Redis)**: Heavy Gemini 3.1 audio processing and TTS audio synthesis are offloaded to distributed background workers with automatic in-process fallback for local dev.
- **🐘 Dual-Database Architecture (PostgreSQL & SQLite)**: Seamlessly operates on embedded SQLite (`aiosqlite`) for local development, and scales to high-concurrency managed PostgreSQL (`asyncpg`) connection pooling in cloud environments.
- **Enterprise Clean Architecture**: Strict decoupling of transport (`bot/`), distributed execution (`worker/`), domain business logic (`services/`), and data access (`repositories/`).

---

## 🏛️ Project Structure

```
speaking-coach-bot/
├── api/
│   └── index.py                      # ⚡ FastAPI Vercel Serverless Webhook Adapter
├── src/
│   ├── bot/                          # Transport / Presentation Layer
│   │   ├── handlers/
│   │   │   ├── common.py             # /start, /scenario, /review, /voice, /level, /progress
│   │   │   ├── ielts_mock.py         # /mock_ielts state machine & blind listening delivery
│   │   │   ├── phonemes.py           # /phonemes catalog, drills, & on-demand audio
│   │   │   ├── tenses.py             # /tenses active grammar & tense speaking gym
│   │   │   ├── reminder.py           # /remind settings menu & custom time parsing
│   │   │   └── voice.py              # Voice note receiver, audio analysis, & routing
│   │   ├── middlewares/
│   │   │   └── user_tracker.py       # Activity interceptor & auto registration
│   │   └── keyboards/
│   │       └── menu.py               # Menus, scenario, voice, level, IELTS, reminder, & phonemes
│   │
│   ├── worker/                       # Distributed Asynchronous Execution Layer
│   │   ├── arq_worker.py             # Background Arq consumer (Gemini audio + edge-tts)
│   │   └── dispatcher.py             # Hybrid VoiceJobDispatcher (Queue or In-process fallback)
│   │
│   ├── services/                     # Business Logic Layer (Pure Domain)
│   │   ├── ai_coach_service.py       # Gemini 3.1 audio evaluation, IELTS packs, & minimal pairs
│   │   ├── reminder_service.py       # Duolingo persona message bank & background worker loop
│   │   ├── tts_service.py            # Neural Text-to-Speech (edge-tts)
│   │   └── user_service.py           # User profiles, streaks, XP, & session states
│   │
│   ├── repositories/                 # Data Access Layer (Dual-Repository Pattern)
│   │   ├── coach_repository.py       # ICoachRepository & SQLite operations (aiosqlite)
│   │   ├── postgres_coach_repository.py # Production PostgreSQL operations (asyncpg)
│   │   ├── database.py               # SQLite schema initializer
│   │   └── __init__.py               # create_coach_repository factory
│   │
│   ├── config.py                     # Pydantic environment validation & port bindings
│   └── __init__.py
│
├── tests/                            # Comprehensive Unit & Webhook Tests (100% PASS - 75 tests)
│   ├── test_ai_coach_service.py      # Core Gemini audio & pedagogical modes tests
│   ├── test_postgres_repository.py   # PostgreSQL repository & connection pool tests
│   ├── test_worker_queue.py          # Arq dispatcher & execution worker tests
│   ├── test_tenses_service.py        # Tenses speaking gym test suite
│   ├── test_state_isolation.py       # Session & drill isolation tests
│   ├── test_gamification_and_tma.py  # Streaks, badges, and XP tests
│   ├── test_qa_qc_security.py        # Security & input sanitization tests
│   └── test_vercel_webhook.py        # Vercel FastAPI webhook & secret token tests
├── manage_webhook.py                 # 🛡️ CLI & Automated Webhook Failover Watchdog
├── vercel.json                       # Vercel serverless rewrite rules
├── compose.yaml                      # Multi-container orchestration (App, Worker, Redis, Postgres)
├── Dockerfile                        # Production container build
├── requirements.txt
├── .env.example
├── .env
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.11+ (Python 3.13 recommended)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/) *(Free tier available)*

### 2. Setup Virtual Environment (WAJIB / MANDATORY)

> [!IMPORTANT]
> **Mengapa Virtual Environment (`venv`) WAJIB digunakan?**
> 1. **Isolasi Dependensi**: Mencegah konflik library antara bot satu dengan bot lainnya di monorepo ini.
> 2. **Standar Python Modern (PEP 668)**: Menghindari error `externally-managed-environment` pada Python 3.11+.
> 3. **Keamanan Sistem**: Memastikan instalasi package tidak merusak instalasi Python global pada OS Anda.

Jalankan perintah berikut di terminal:
```bash
# 1. Buat virtual environment
python -m venv venv

# 2. Aktifkan virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# (Jika muncul batasan skrip di PowerShell: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)

# Linux / macOS:
source venv/bin/activate

# 3. Install dependensi:
pip install -r requirements.txt
```

### 3. Configure Environment
Edit `.env`:
```env
BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=AIzaSyYourGeminiApiKeyHere
GEMINI_MODEL=gemini-3.1-flash-lite
BOT_MODE=polling
DATABASE_PATH=speaking_coach.db
```

### 4. Run Locally
```bash
python main.py
```

### 5. Run Unit Tests
```bash
python -m unittest discover tests
```

---

## 🎮 Command Reference

| Command | Action |
| :--- | :--- |
| `/start` | Open welcome greeting and primary menu |
| `/dashboard` | Open interactive visual Telegram Mini App dashboard |
| `/upgrade` | Upgrade to Lifetime Premium Pass via Telegram Stars (`XTR`) |
| `/mock_ielts` | Full 3-Part IELTS Speaking Mock Exam (FC, LR, GRA, PR Scorecard) |
| `/shadow` | Shadowing mode (Pronunciation accuracy & cadence matching) |
| `/phonemes` | Phonetics clinic & minimal pairs drill (/θ/ vs /s/, /v/ vs /b/, etc.) |
| `/scenario` | Pick roleplay mode (Job Interview, Cafe, Airport, Tech Standup) |
| `/review` | Review personal vocabulary bank and flagged grammar slips |
| `/voice` | Switch between US and UK neural spoken reply voices |
| `/level` | Adjust target proficiency (Beginner, Intermediate, Advanced) |
| `/topic` | Generate a curated speaking prompt for your current level |
| `/remind` | Configure proactive daily practice reminders (🔥 streak protector) |
| `/progress` | View streak, rank tier, XP, badges, and IELTS scorecards |
| `/help` | Detailed usage instructions |

---

## 🚀 Deployment Guide

Aplikasi ini mendukung dua mode eksekusi (**Long Polling** & **Webhook HTTPS**) yang siap di-deploy secara gratis maupun ke server produksi:

### 1. ⚡ Free Cloud Deployment (Vercel Serverless + Neon PostgreSQL)

Vercel menyediakan **Serverless Function** global yang aktif **24/7 tanpa batas kapasitas**, dipadukan dengan database cloud serverless dari **[Neon.tech](https://neon.tech)**. Kombinasi ini 100% gratis, tanpa kartu kredit, dan memastikan bot selalu online secara permanen.

#### 🌟 Keunggulan Vercel + Neon.tech:
- 🟢 **100% Gratis & Tanpa Kartu Kredit**: Cukup login menggunakan akun GitHub Anda.
- 🟢 **Serverless Uptime Global**: Tidak pernah "out of capacity" atau terhenti akibat server penuh.
- 🟢 **Database Cloud Permanen**: PostgreSQL Neon.tech menyimpan streak, skor IELTS, riwayat review, dan XP selamanya secara persisten.
- 🟢 **Keamanan Berlapis**: Validasi webhook menggunakan header rahasia `X-Telegram-Bot-Api-Secret-Token`.

#### 📋 Langkah-langkah Deployment:

1. **Siapkan Database PostgreSQL di Neon.tech (30 Detik)**:
   - Buka [https://neon.tech](https://neon.tech) lalu login dengan GitHub (100% gratis, tanpa kartu kredit).
   - Klik **Create Project** (misal: `speaking-coach-db`).
   - Salin connection string PostgreSQL. Disarankan memilih opsi **Connection Pooling** (mengandung `-pooler`):
     ```text
     postgresql://neondb_owner:PASSWORD@ep-xyz-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
     ```

2. **Deploy ke Vercel**:
   - Buka [https://vercel.com](https://vercel.com) dan login menggunakan akun GitHub Anda.
   - Klik **Add New...** -> **Project**, lalu impor repository **`TinoNurcahya/telegram-bots`**.
   - Pada bagian **Root Directory**, klik **Edit** lalu pilih: **`apps/speaking-coach-bot`**.
   - Pada bagian **Environment Variables**, tambahkan 4 variabel berikut:
     | Key | Value | Keterangan |
     | :--- | :--- | :--- |
     | `BOT_TOKEN` | `your_bot_token` | Token bot dari @BotFather |
     | `GEMINI_API_KEY` | `your_gemini_key` | API Key dari Google AI Studio |
     | `DATABASE_URL` | `postgresql://...` | Connection string Neon.tech (pooled) |
     | `WEBHOOK_SECRET` | `your_secret_token` | String rahasia untuk verifikasi webhook Telegram |
   - Klik **Deploy**. Vercel akan menerbitkan URL aplikasi Anda dalam ~30 detik (contoh: `https://speaking-coach-bot.vercel.app`).

3. **Aktifkan Telegram Webhook**:
   - Buka browser atau jalankan perintah curl untuk mendaftarkan URL webhook ke Telegram:
     ```bash
     curl -F "url=https://<VERCEL_URL>/api/index" \
          -F "secret_token=<WEBHOOK_SECRET>" \
          https://api.telegram.org/bot<BOT_TOKEN>/setWebhook
     ```
   - Respons sukses:
     ```json
     {"ok": true, "result": true, "description": "Webhook was set"}
     ```

4. **(Opsional) Custom Domain & Failover Management**:
   - Jika memiliki domain kustom (misal: `speaking-coach-bot.tinonurcahya.dev`), tambahkan di menu **Vercel Settings -> Domains**.
   - Anda dapat memeriksa status atau mengganti target webhook secara instan menggunakan script bawaan:
     ```bash
     python manage_webhook.py --status
     python manage_webhook.py --auto
     ```
   - Watchdog otomatis di [`.github/workflows/webhook-watchdog.yml`](../../.github/workflows/webhook-watchdog.yml) memantau domain secara berkala dan otomatis mengalihkan webhook ke domain fallback `vercel.app` jika domain utama tidak aktif.

---

### 2. 🐳 Docker & Docker Compose Deployment (Local / VPS)

Untuk menjalankan bot dalam kontainer terisolasi di server VPS atau komputer lokal:

#### Opsi A: Menggunakan Docker Compose (Direkomendasikan)
```bash
# Jalankan container di background
docker compose -f compose.yaml up -d --build

# Periksa log aktivitas bot
docker compose -f compose.yaml logs -f

# Hentikan container
docker compose -f compose.yaml down
```

#### Opsi B: Build Docker Image Manual
```bash
docker build -t speaking-coach-bot:latest .
docker run -d --name tg-speaking-coach --env-file .env -v $(pwd)/data:/app/data speaking-coach-bot:latest
```

---

### 3. 🐧 Linux VPS Service (Systemd Native)

Jika menjalankan bot langsung di Ubuntu/Debian VPS menggunakan Python virtual environment:

1. Buat file service:
   ```bash
   sudo nano /etc/systemd/system/speaking-coach.service
   ```
2. Isi konfigurasi:
   ```ini
   [Unit]
   Description=Telegram Speaking Coach Bot
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/telegram-bots/apps/speaking-coach-bot
   ExecStart=/home/ubuntu/telegram-bots/apps/speaking-coach-bot/venv/bin/python main.py
   Restart=always
   RestartSec=5
   EnvironmentFile=/home/ubuntu/telegram-bots/apps/speaking-coach-bot/.env

   [Install]
   WantedBy=multi-user.target
   ```
3. Aktifkan dan jalankan:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable speaking-coach
   sudo systemctl start speaking-coach
   sudo systemctl status speaking-coach
   ```

---

## 📄 License & Terms

Copyright (c) 2026 Tino Nurcahya. All rights reserved.  
Proprietary & confidential for portfolio showcase only. Strictly **NOT** for commercial use.
