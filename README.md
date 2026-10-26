# 🤖 Telegram Bots Portfolio Showcase

A curated monorepo showcasing production-grade, asynchronous Telegram bots built with **Python (`aiogram v3`)** and **TypeScript (`grammY`)**, deployed with modern cloud serverless and container architectures. 

Designed with modular architectures, embedded SQLite persistence, and a hybrid execution engine (instant local Long Polling with seamless Webhook deployment).

---

## 🏛️ Monorepo Architecture

This repository adopts a modular **`apps/`** monorepo pattern. Each bot project operates independently with its own runtime dependencies, configuration schema, and container specification:

```
telegram-bots/
├── .github/
│   └── workflows/
│       └── webhook-watchdog.yml     # 🛡️ 24/7 Failover watchdog & 60-day keepalive
├── apps/
│   └── speaking-coach-bot/          # 🎙️ AI Speaking Coach (Python 3.13 + Gemini 3.1 Flash-Lite Multimodal Audio)
│       ├── api/
│       │   └── index.py             # ⚡ FastAPI Vercel Serverless Webhook Adapter
│       ├── src/
│       │   ├── bot/                 # Handlers (voice notes, tenses, phonemes, IELTS, reminders)
│       │   ├── services/            # Gemini audio analysis, TTS, user XP, streaks, dialogue FSM
│       │   ├── repositories/        # Dual SQLite / Neon PostgreSQL repository factory
│       │   └── config.py            # Pydantic environment validation & port bindings
│       ├── tests/                   # 77/77 Comprehensive Unit & Webhook Tests
│       ├── main.py                  # Local Polling & Docker Webhook runner
│       ├── manage_webhook.py        # CLI for primary/fallback webhook management
│       ├── vercel.json              # Vercel serverless rewrite rules
│       ├── compose.yaml
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── .env.example
│       └── README.md
├── .gitignore
├── LICENSE                          # Proprietary portfolio license
└── README.md
```

---

## 📦 Showcase Catalog

| Bot Project | Stack | Highlights | Status & Live Bot |
| :--- | :--- | :--- | :--- |
| **[apps/speaking-coach-bot](apps/speaking-coach-bot)** | Python 3.13, `aiogram v3`, Gemini 3.1 Flash-Lite Multimodal, `edge-tts`, FastAPI, Neon PostgreSQL | Live `.ogg` voice note analysis, IELTS 3-part mock exam, tenses gym, phonemes clinic, 24/7 Vercel Serverless + custom domain failover | 🟢 **Production Live**<br>🤖 Bot: [@MyEnglishCoach2000_bot](https://t.me/MyEnglishCoach2000_bot)<br>🌐 Endpoint: [speaking-coach-bot.tinonurcahya.dev](https://speaking-coach-bot.tinonurcahya.dev) |

---

## ⚡ Core Features

- **Hybrid Operational Modes**:
  - **Local Development**: Instant **Long Polling** without requiring public domains, ngrok, or SSL certificates.
  - **Production Deployment**: Switch to **Webhooks** simply by setting `BOT_MODE=webhook` and `WEBHOOK_URL` in `.env`.
- **Zero-Config Database**: Embedded SQLite tracking registered users, message frequencies, first-seen timestamps, and activity analytics.
- **Interactive UI**: Inline button menus with dynamic callbacks and real-time latency ping diagnostics.
- **Docker Ready**: Individual Dockerfiles and modular Docker Compose services configured per application.

---

## 🚀 Quick Start Guide

### Step 1: Clone Repository
```bash
git clone https://github.com/TinoNurcahya/telegram-bots.git
cd telegram-bots
```

### Option A: Run the AI Speaking Coach Bot (Local Python venv)

> [!IMPORTANT]
> **Virtual Environment (`venv`) WAJIB DIGUNAKAN:**
> Jangan install paket Python langsung ke environment global OS untuk menghindari konflik dependensi antar bot atau error PEP 668 (`externally-managed-environment`).

```bash
cd apps/speaking-coach-bot

# 1. Buat virtual environment (wajib)
python -m venv venv

# 2. Aktifkan venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# (Jika muncul batasan skrip di PowerShell: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)

# Linux / macOS:
source venv/bin/activate

# 3. Install dependencies ke dalam venv:
pip install -r requirements.txt

# 4. Konfigurasi kredensial di .env
# Isi BOT_TOKEN (dari @BotFather) dan GEMINI_API_KEY (dari Google AI Studio)

# 5. Jalankan bot:
python main.py
```

### Option B: Run via Docker Compose
Jalankan bot beserta stack dependensinya menggunakan Docker Compose langsung dari foldernya:
```bash
cd apps/speaking-coach-bot
docker compose up -d
```

### Option C: 100% Free Production Cloud Deployment (Vercel + Neon PostgreSQL)
Speaking Coach AI Bot beroperasi 24/7 di infrastruktur cloud serverless tanpa biaya dan tanpa kartu kredit:
- 🌐 **Primary Production Domain**: [https://speaking-coach-bot.tinonurcahya.dev](https://speaking-coach-bot.tinonurcahya.dev)
- 🛡️ **Fallback Production Domain**: [https://speaking-coach-bot.vercel.app](https://speaking-coach-bot.vercel.app)
- 🐘 **Managed Database**: [Neon.tech](https://neon.tech) Serverless PostgreSQL (Singapore Region, pooling enabled)
- 🔄 **Automated Failover Watchdog**: [`.github/workflows/webhook-watchdog.yml`](.github/workflows/webhook-watchdog.yml) memantau domain setiap 6 jam dan otomatis mengalihkan webhook Telegram ke `vercel.app` jika domain dev mengalami kendala.

Panduan lengkap langkah-langkah deployment tersedia di [apps/speaking-coach-bot/README.md](apps/speaking-coach-bot/README.md#1-️-free-cloud-deployment-vercel-serverless--neon-postgresql).

---

## 🎮 Standard Command Reference

Core commands implemented in the bot suite:

| Command | Action |
| :--- | :--- |
| `/start` | Welcomes user and displays inline menu (activity auto-tracked via middleware) |
| `/help` | Detailed command manual and usage instructions |
| `/status` | Measures real-time round-trip latency (ping), active mode, and registered user count |
| `/stats` | Fetches personal interaction statistics and timestamps via domain service |
| `/about` | Displays project architecture, author information, and portfolio license |

---

## 🏗️ Architectural Guidelines

All bots in this repository adhere to production-ready enterprise standards:

### 1. Baseline Standard: Clean / Layered Architecture
Every bot is strictly organized into decoupled layers:
```text
src/
├── bot/
│   ├── handlers/      # Transport / Telegram commands & events
│   ├── middleware/    # Auth, user tracking, rate-limiting, error logging
│   └── keyboards/     # Inline & reply keyboards
├── services/          # Pure business logic (framework & Telegram agnostic)
├── repositories/      # Data access layer (SQL / ORM queries)
├── config.ts          # Typed configuration loader
└── index.ts           # Bootstrapper & entrypoint
tests/                 # Unit & integration tests
```
* **Strict Production Rules**:
  - `handlers/` must **never** call database queries directly; they must delegate to `services/`.
  - `services/` must **never** reference Telegram objects (`ctx`, `Message`, `Bot`); they accept pure DTOs/primitives to guarantee testability.
  - `repositories/` abstract database drivers so DB engines (SQLite to PostgreSQL/Prisma) can be swapped without touching business logic.
  - Cross-cutting concerns (user activity logging, latency) must be handled in `middleware/`, keeping handlers focused.

### 2. Scaling Path: Vertical Slice Architecture (Feature-First)
When an individual bot grows into a multifunctional application (e.g., e-commerce, AI assistant, subscriptions), transition to feature slices:
```text
src/
├── features/
│   ├── ai-chat/       # handler, service, model client
│   ├── subscription/  # handler, service, invoice gateway, repo
│   └── moderation/    # handler, filters, anti-spam rules
├── shared/            # Shared DB connection, middleware, utilities
└── index.ts
```

### 3. Interactive Pattern: FSM / Conversation Scene Architecture (State-Driven)
For multi-step dialogs (registration wizards, quiz flows, checkout forms):
* **Best For**: Step-by-step user interactions requiring state memory between messages.
* **Framework Implementations**:
  - **Python**: `aiogram.fsm` (`StatesGroup`, `FSMContext` backed by Memory / Redis / SQLite).
  - **TypeScript**: `@grammyjs/conversations` (linear async/await conversation runner) or Scenes.
* **Structure**:
  ```text
  src/
  ├── bot/
  │   └── conversations/     # Multi-step conversational wizards
  │       ├── kyc-flow.ts    # Step 1: Name -> Step 2: ID card -> Step 3: Confirmation
  │       └── order-flow.ts
  ```
* **Rule**: Store session state in persistent storage (e.g., Redis or SQLite) rather than process memory so active dialogues survive container restarts.

### 4. High-Throughput Pattern: Queue-Worker / Event-Driven Architecture
Essential for heavy workloads such as media downloaders (YouTube, TikTok), video/audio transcoding, PDF conversions, scraping, or heavy AI/LLM generation:
* **The Telegram Constraint**: Telegram webhooks strictly require HTTP 200 response within 3–5 seconds. Long-running tasks executed directly in the update handler will trigger webhook timeouts and infinite duplicate update retries.
* **Architecture Flow**:
  ```
  [ Telegram User ]
         │
         ▼
  [ Webhook / Polling Receiver ] ──► Instant reply (< 2s): "Processing your request... ⏳"
         │
         ▼ (Push Job)
  [ Queue: Redis / BullMQ / Celery ]
         │
         ▼ (Asynchronous Consumption)
  [ Background Workers (1..N) ] ──► Heavy download / transcoding / AI inference
         │
         ▼ (On Complete)
  [ Telegram Bot API ] ──► Sends final file or result back to the user
  ```
* **Rule**: Decouple the update listener from execution workers. Handlers only validate commands, enqueue jobs, and return immediate user feedback.

### 5. Multi-Platform Pattern: Hexagonal / Omni-Channel Architecture
When the bot's core service must be accessible across multiple chat apps (Telegram, WhatsApp, Discord, or Web):
* Keep the **Core Domain** completely independent of any messaging platform.
* Implement Telegram as a *Driving Adapter* alongside WhatsApp and Discord adapters.

---

### 📊 Architecture Selection Matrix

| Pattern | Primary Focus | Best Use Cases |
| :--- | :--- | :--- |
| **Clean / Layered** | Code quality & testability | Standard bots, business rules, structured CRUD |
| **Vertical Slice** | Modularity & domain isolation | Large super-bots with independent feature modules |
| **FSM / Conversations** | Multi-step interactive dialogs | KYC, surveys, multi-step booking, onboarding wizards |
| **Queue-Worker** | Performance & latency prevention | Media downloaders, video/audio convert, AI LLM processing |
| **Hexagonal** | Omni-channel flexibility | Shared bots across Telegram, WhatsApp, and Discord |

---

## 💡 Project Roadmap & Exploration Ideas

| # | Proyek | Nilai Portofolio | Monetisasi | Dipakai Sendiri | Keseruan | Kompleksitas | Status |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Bot pesanan UMKM + dashboard (katalog, keranjang, pembayaran, dashboard pemilik) | Tinggi | Tinggi | Rendah | Sedang | Sedang | 📋 Planned |
| **2** | **Bot latihan speaking (voice note transcript, grammar, & pelafalan via AI)** | **Sangat Tinggi** | **Rendah-Sedang** | **Tinggi** | **Tinggi** | **Sedang** | **🟢 Built ([speaking-coach-bot](apps/speaking-coach-bot))** |
| **3** | Bot lowongan kerja niche (developer di Jepang/Australia, dari RSS/API resmi) | Sedang | Rendah-sedang | Tinggi | Sedang | Sedang | 📋 Planned |
| **4** | Bot pengingat dan deadline (gaya Skeddy/AlertBot, untuk tugas dan jadwal kuliah) | Rendah-sedang | Rendah | Tinggi | Sedang | Rendah | 📋 Planned |
| **5** | Bot OCR/voice-to-text (foto catatan jadi teks, voice note jadi teks; gaya Texify/Voicy) | Sedang-tinggi | Sedang (freemium + Stars) | Tinggi | Sedang | Sedang | 📋 Planned |
| **6** | Bot digest berita/RSS + ringkasan AI (gaya Feed Reader) | Sedang | Rendah | Tinggi | Sedang | Rendah | 📋 Planned |
| **7** | Bot catat pengeluaran lewat chat (“makan siang 15rb” langsung tercatat dan dikategorikan) | Sedang | Rendah | Tinggi | Sedang | Rendah-sedang | 📋 Planned |
| **8** | Bot kuis/trivia untuk grup kampus (gaya QuizBot) | Rendah | Rendah | Sedang | Tinggi | Rendah | 📋 Planned |
| **9** | Bot language exchange (pencocokan pasangan latihan) | Tinggi (logika matching) | Rendah | Sedang | Tinggi | Tinggi | 📋 Planned |
| **10** | Telegram Mini App store (versi web dari #1, Next.js di dalam Telegram) | Tinggi | Sedang-tinggi | Rendah | Sedang | Tinggi | 📋 Planned |

---

## 📄 License & Terms

Copyright (c) 2026 Tino Nurcahya. All rights reserved.

This project and its code are proprietary and confidential. It is made available solely for portfolio demonstration and personal evaluation purposes. This project is strictly **NOT** intended for commercial use. Unauthorized copying, modification, distribution, commercial exploitation, or use of this file and its codebase via any medium is strictly prohibited.