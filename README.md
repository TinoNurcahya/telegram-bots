# 🤖 Telegram Bots Portfolio Showcase

A curated monorepo showcasing production-grade, asynchronous Telegram bots built with **Python (`aiogram v3`)** and **TypeScript (`grammY`)**. 

Designed with modular architectures, embedded SQLite persistence, and a hybrid execution engine (instant local Long Polling with seamless Webhook deployment).

---

## 🏛️ Monorepo Architecture

This repository adopts a modular **`apps/`** monorepo pattern. Each bot project operates independently with its own runtime dependencies, configuration schema, and container specification:

```
telegram-bots/
├── apps/
│   ├── speaking-coach-bot/      # 🎙️ AI Speaking Coach (Python 3.13 + Gemini 2.0 Audio + aiogram v3)
│   │   ├── src/
│   │   │   ├── bot/             # Handlers (voice note receiver), middlewares, keyboards
│   │   │   ├── services/        # Gemini multimodal audio evaluation & user progress
│   │   │   ├── repositories/    # SQLite session history & user profiles
│   │   │   └── config.py
│   │   ├── tests/               # Unit tests (Mock AI & session tracking)
│   │   ├── main.py
│   │   ├── compose.yaml
│   │   ├── Dockerfile
│   │   └── README.md
│   │
│   ├── python-starter/          # Python 3.13 + aiogram v3 + aiosqlite (Clean Architecture)
│   │   ├── src/
│   │   │   ├── bot/             # Transport layer (handlers, middlewares, keyboards)
│   │   │   ├── services/        # Domain business logic (pure & testable)
│   │   │   ├── repositories/    # Data access layer (database & queries)
│   │   │   └── config.py        # Pydantic settings & validation
│   │   ├── tests/               # Unit & integration tests
│   │   ├── main.py              # Polling & aiohttp Webhook runner
│   │   ├── compose.yaml
│   │   ├── Dockerfile
│   │   └── README.md
│   │
│   └── ts-starter/              # TypeScript + grammY + Node 22 SQLite (Clean Architecture)
│       ├── src/
│       │   ├── bot/             # Transport layer (handlers, middlewares, keyboards)
│       │   ├── services/        # Domain business logic (pure & testable)
│       │   ├── repositories/    # Data access layer (database & queries)
│       │   └── config.ts        # Typed environment schema
│       ├── tests/               # Unit & integration tests
│       ├── index.ts             # Polling & Express Webhook runner
│       ├── compose.yaml
│       ├── Dockerfile
│       └── README.md
│
├── compose.yaml                 # Multi-bot container orchestration
├── .gitignore
├── LICENSE                      # Proprietary portfolio license
└── README.md
```

---

## 📦 Showcase Catalog

| Bot Project | Stack | Highlights | Status |
| :--- | :--- | :--- | :--- |
| **[apps/speaking-coach-bot](apps/speaking-coach-bot)** | Python 3.13, `aiogram v3`, Gemini 2.0 | Native `.ogg` audio ingestion, grammar analysis, pronunciation tips, conversation partner | 🟢 Active Showcase |
| **[apps/python-starter](apps/python-starter)** | Python 3.13, `aiogram v3`, `aiosqlite` | Clean Architecture boilerplate, Pydantic settings, aiohttp webhooks | 🟢 Production Ready |
| **[apps/ts-starter](apps/ts-starter)** | TypeScript, `grammY`, Node 22 `node:sqlite` | Clean Architecture boilerplate, zero external DB dependencies, Express webhooks | 🟢 Production Ready |

---

## ⚡ Core Features

- **Hybrid Operational Modes**:
  - **Local Development**: Instant **Long Polling** without requiring public domains, ngrok, or SSL certificates.
  - **Production Deployment**: Switch to **Webhooks** simply by setting `BOT_MODE=webhook` and `WEBHOOK_URL` in `.env`.
- **Zero-Config Database**: Embedded SQLite tracking registered users, message frequencies, first-seen timestamps, and activity analytics.
- **Interactive UI**: Inline button menus with dynamic callbacks and real-time latency ping diagnostics.
- **Docker Ready**: Individual Dockerfiles and a root `docker-compose.yml` to spin up any or all bots with one command.

---

## 🚀 Quick Start Guide

### Step 1: Clone & Choose an App
```bash
git clone https://github.com/TinoNurcahya/telegram-bots.git
cd telegram-bots
```

### Option A: Run the AI Speaking Coach Bot (Python)

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

### Option B: Run the TypeScript Bot
```bash
cd apps/ts-starter

# Install dependencies
npm install                    # Or cmd /c npm install on restricted Windows shells

# Configure token
cp .env.example .env
# Edit BOT_TOKEN in .env

# Run bot (development with hot-reload)
npm run dev
```

### Option C: Run via Docker Compose
Ensure `.env` files are configured in both app folders, then run:
```bash
docker compose up -d
```

### Option D: 100% Free Cloud Deployment (Vercel Serverless)
Panduan lengkap step-by-step deploy gratis ke cloud tanpa kartu kredit dan 24/7 online tersedia di [apps/speaking-coach-bot/README.md](apps/speaking-coach-bot/README.md#1-️-free-cloud-deployment-vercel-serverless--100-gratis-tanpa-kartu-kredit--selalu-online).

---

## 🎮 Standard Command Reference

Both starter bots implement consistent core commands:

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