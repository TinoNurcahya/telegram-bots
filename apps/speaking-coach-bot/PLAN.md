# 🎙️ Product Roadmap & Engineering Master Plan: AI Speaking Coach Bot

**Project:** `apps/speaking-coach-bot`  
**Current Status:** Production-Ready (All Phases 1–10 Completed)  
**Contact:** `tinonurcahya.ti@gmail.com`  
**Architecture:** Clean / Layered Architecture  

---

## 📌 1. Executive Summary

The **AI English Speaking Coach Bot** is designed to eliminate the psychological friction, high expense, and scheduling barriers associated with traditional foreign language conversation practice. 

By leveraging **direct voice note ingestion** (Telegram `.oga`/`.ogg` audio) coupled with **Google Gemini 2.0 Multimodal Audio** and **neural Text-to-Speech (`edge-tts`)**, the bot provides immediate, pedagogical feedback and an interactive conversational partner that speaks back directly inside Telegram chat.

This document serves as the canonical engineering blueprint, detailing:
1. Implemented features and architectural baseline (Phase 1).
2. Advanced pedagogical practice modes (Phase 2).
3. Gamification and retention mechanics (Phase 3).
4. Enterprise cloud infrastructure and scalability roadmap (Phase 4).

---

## ✅ 2. Phase 1: Completed Features & Baseline Architecture

The foundational architecture is deployed, fully functional, and verified with a 100% passing test suite.

```
┌──────────────────────────────────────────────────────────────┐
│                    TELEGRAM CLIENT (USER)                    │
│      [Voice Note .oga] ──▲               │ [/start, /topic]  │
│                          │ [Voice + Text]│                   │
└──────────────────────────┼───────────────┼───────────────────┘
                           │               ▼
┌──────────────────────────┼───────────────────────────────────┐
│ TRANSPORT LAYER          │ Bot Dispatcher (aiogram v3)       │
│  - UserTrackerMiddleware └──► common.py & voice.py           │
└──────────────────────────────────────────┬───────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────┐
│ DOMAIN SERVICES                          │                   │
│  - AICoachService (Gemini 2.0 Audio)     │ UserService       │
│  - TTSService (edge-tts Neural Audio)    │                   │
└──────────────────────────────────────────┬───────────────────┘
                                           │
┌──────────────────────────────────────────▼───────────────────┐
│ DATA ACCESS LAYER (SQLite via aiosqlite)                     │
│  - CoachRepository (users, sessions, vocab_bank)             │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 Implemented Capabilities

| Component | Implemented Capability | Technical Highlights |
| :--- | :--- | :--- |
| **Voice Note Ingestion** | Direct processing of Telegram `.oga` / `.ogg` audio files | Zero FFmpeg transcoding requirement; direct in-memory binary streaming to Gemini API |
| **Multimodal Speech Analysis** | Comprehensive pronunciation, grammar, and fluency evaluation | Single-pass Gemini 2.0 Flash prompt returning structured Pydantic JSON schema |
| **Neural Voice Replies** | AI speaks back to the user with a realistic voice note | Asynchronous `edge-tts` synthesis with US and UK native neural voice profiles |
| **CEFR & IELTS Estimator** | Objective linguistic grading per session | Quantitative Fluency Score (1-100), CEFR Level (A1–C2), and estimated IELTS Band (4.0–8.5) |
| **Roleplay Scenarios** | Situational contextual training (`/scenario`) | 5 distinct modes: Job Interview, Cafe & Dining, Airport Immigration, Tech Standup, and Free Chat |
| **Weak-Word & Vocab Bank** | Automated mistake tracking (`/review`) | Intercepts grammar slips and awkward phrasing, automatically archiving them to SQLite for later review |
| **Adaptive Difficulty** | Dynamic difficulty calibration (`/level`) | Beginner (A1-A2), Intermediate (B1-B2), and Advanced (C1-C2) vocabulary calibration |
| **Clean Architecture** | Strict presentation, service, and data access decoupling | `services/` contains zero framework imports; 100% testable via Mock repositories |

---

## 🎯 3. Phase 2: Advanced Pedagogical & Practice Modes (Short-Term)

Phase 2 focuses on deepening educational value with specialized practice modes tailored for test-takers and serious learners.

```
                                  [ PRACTICE MODES ]
                                           │
            ┌──────────────────────────────┼──────────────────────────────┐
            ▼                              ▼                              ▼
    [ Shadowing Mode ]            [ IELTS Mock Exam ]            [ Phoneme Visualizer ]
  Audio playback -> Echo        Full 3-Part Exam Simulation    Syllable & Sound Comparison
   Pitch & Rhythm match           Official IELTS Scorecard       Minimal Pairs (/θ/ vs /s/)
```

### 3.1 Mode A: Native Shadowing & Intonation Matching (`/shadow`)
* **Objective**: Train rhythm, cadence, and muscle memory by mimicking native speech chunks.
* **Workflow**:
  1. The bot sends a short native audio snippet (3–7 seconds) with marked intonation curves.
  2. The learner listens and sends back their voice note attempting to match speed and pitch.
  3. The service computes a **Levenshtein Word Accuracy score** and **Pacing/Cadence similarity score** (0–100%).
  4. Bot returns highlighted words where timing or stress was skipped.

### 3.2 Mode B: Full 3-Part IELTS Speaking Mock Exam (`/mock_ielts`)
* **Objective**: Replicate the official 11–14 minute IELTS Speaking interview.
* **Structure**:
  - **Part 1 (Introduction & Interview, 4-5 mins)**: 4 rapid questions on home, work, and interests.
  - **Part 2 (The Long Turn, 3-4 mins)**: Bot displays a Cue Card; provides an automated 60-second preparation timer, then records a 2-minute uninterrupted monologue.
  - **Part 3 (Two-way Discussion, 4-5 mins)**: Abstract, analytical questions challenging the candidate's arguments.
* **Deliverable**: Comprehensive **Official Band Score Report** broken down into the 4 official IELTS criteria:
  - *Fluency and Coherence (FC)*
  - *Lexical Resource (LR)*
  - *Grammatical Range and Accuracy (GRA)*
  - *Pronunciation (PR)*

### 3.3 Mode C: Phoneme-Level Diffing & Minimal Pairs (`/phonemes`)
* **Objective**: Correct chronic pronunciation blindspots (e.g., distinguishing `/θ/` in *think* vs `/s/` in *sink*, or `/v/` vs `/b/`).
* **Implementation**: Gemini phonetic token analysis identifying exact misplaced phonemes with phonetic spelling guides (IPA).

---

## 🔥 4. Phase 3: Gamification, Habit Formation & Retention (Mid-Term)

Language acquisition requires consistency. Phase 3 introduces behavioral habit loops to convert casual users into daily learners.

### 4.1 Daily Practice Streak Engine (`🔥 Streaks`)
* **Streak Logic**:
  - Requires at least **1 evaluated voice note** per calendar day (UTC or user timezone).
  - Streak milestones trigger celebration banners and visual Telegram badges (🔥 7 Days, 🔥 30 Days, 🔥 100 Days).
  - **Streak Freeze Protection**: Users can earn or purchase 1 freeze pass per month to preserve streaks during travel.

### 4.2 Proactive Scheduled Practice Notifications
* **Mechanism**: Background scheduler (APScheduler / Cron Worker) dispatching non-intrusive reminder alerts:
  ```
  "⏰ 2-Minute Speaking Check-in!
   Your 14-day streak is active 🔥. 
   Today's prompt: 'What was the highlight of your morning?'
   Tap and hold the mic to record your response!"
  ```
* Configurable reminder window (`/settings -> Remind me at 08:00 AM / 08:00 PM`).

### 4.3 XP, Levels & Achievement Badges
* **Progression Model**:
  - 10 XP per voice note practice.
  - 50 XP bonus for completing daily topic.
  - 100 XP bonus for IELTS Mock Exam.
* **Tier Progression**:
  - *Level 1–3: Language Explorer*
  - *Level 4–6: Confident Conversationalist*
  - *Level 7–9: Fluent Debater*
  - *Level 10: Native Master*

### 4.4 100% Native Telegram In-Chat Progress Card & Scorecard (`/progress`)
* **Format**: Pure Telegram interactive rich text card rendered directly in the chat with dynamic inline keyboard controls (`[ 🔄 Refresh Data ]`, `[ ⏳ Klinik Tenses ]`, `[ 👄 Latihan Fonem ]`).
* **Design Philosophy**: 100% native Telegram experience—zero external browser web latency, zero web app popups.
* **Features**:
  - Visual XP level progress bar (`▓▓▓▓▓▓░░░░ 60%`).
  - Linguistic radar metrics (Fluency, Pronunciation, Grammar, Lexical).
  - Daily streak 🔥 status and Streak Freeze protection shield count.
  - Official IELTS Mock Exam history and latest Band score.
  - Achievement badge gallery unlocked through practice consistency.

---

## ☁️ 5. Phase 4: Enterprise Scalability & Cloud Architecture (Long-Term)

As traffic scales beyond single-instance Long Polling, the bot transitions to an **Asynchronous Queue-Worker architecture**.

```
                           [ TELEGRAM CLOUD ]
                                   │
                                   ▼ (HTTPS Webhook)
                      [ CLOUD RUN / NGINX REVERSE PROXY ]
                                   │
                                   ▼
                       [ BOT WEBHOOK RECEIVER (Fast) ]
                       - Immediate HTTP 200 OK
                       - Pushes job to Redis
                                   │
                                   ▼
                         [ REDIS / ARQ QUEUE ]
                                   │
                                   ▼ (Async Job Consumption)
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
      [ WORKER INSTANCE 1 ]                   [ WORKER INSTANCE 2 ]
      - Gemini Multimodal API                 - Gemini Multimodal API
      - edge-tts Audio Synthesis              - edge-tts Audio Synthesis
      - DB Persistence (PostgreSQL)           - DB Persistence (PostgreSQL)
               │                                       │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼ (Direct Push)
                        [ TELEGRAM BOT API ]
                     - Sends formatted text + voice
```

### 5.1 Architecture Transition Plan

| Dimension | Current (Phase 1) | Target (Phase 4) |
| :--- | :--- | :--- |
| **Connection Mode** | Long Polling / Single-node Webhook | Cloud Run Auto-scaling Webhook with HTTPS |
| **Job Processing** | Synchronous inside Telegram update handler | Asynchronous Job Queue (Redis + Arq / Celery) |
| **Database** | Embedded SQLite (`aiosqlite`) | Managed PostgreSQL (Supabase / Cloud SQL) with connection pooling |
| **Session Cache** | SQLite user table queries | Redis in-memory caching for active dialogue state |
| **Monitoring** | Stdout logging | Structured OpenTelemetry + Sentry error tracing + Prometheus metrics |

### 5.2 Monetization & Telegram Stars (`XTR`) Integration
* **Freemium Tier**: 3 free voice evaluations and 1 daily topic per 24 hours.
* **Premium Pass (Via Telegram Stars)**:
  - Unlimited voice note evaluations.
  - Full access to 3-Part IELTS Mock Exams with official scorecards.
  - Personalized Accent Coach with phoneme-level audio comparison.
  - Telegram Native Payment via `send_invoice` and Stars currency.

---

## 🧠 6. Phase 6: Multi-Turn Dialogue Memory & Conversational Continuity (Completed)

To transform single-turn roleplays into realistic, continuous conversations, Phase 6 introduces stateful dialogue context:

### 6.1 Architecture & Features
* **10-Turn Rolling Window (20 Messages)**: Keeps up to 10 pairs of user voice transcripts and AI responses in memory so the AI remembers past statements, follows up, and doesn't repeat interview questions.
* **Dual-Layer Memory**:
  - Layer 1: Fast Redis cache (`dialogue:{user_id}:{scenario}`) with automatic 2-hour inactivity expiration (7200s TTL).
  - Layer 2: Persistent database storage (`dialogue_turns` table in SQLite/PostgreSQL) with `max_age_hours=2` query filtering.
* **Contextual Openings & Reset Triggers**:
  - `/reset` command to start a clean roleplay slate anytime.
  - Automatically resets when switching scenarios (`/scenario`), immediately delivering a scenario-specific opening icebreaker.

---

---

## 🎁 7. Phase 7: Referral System & Viral Growth Loop (Completed)

To accelerate organic user acquisition and reward loyal learners, Phase 7 introduces deep-linked Telegram referrals:

### 7.1 Architecture & Reward Structure
* **Deep-Linking**: Direct Telegram onboarding via `t.me/<bot_username>?start=ref_<inviter_id>`.
* **Inviter Rewards (Pengundang)**:
  - +1 Streak Freeze Pass per successful friend onboarded.
  - +3 Extra Daily Voice Notes quota.
  - +50 XP bonus for level progression.
  - Real-time instant notification when a friend joins.
* **Invitee Rewards (Teman Baru)**:
  - +3 Welcome Bonus Voice Notes on day one (total 13 voice notes).
  - +25 XP Welcome Bonus.
* **Access & UI**:
  - Commands: `/invite` and `/referral`.
  - Main Menu entry: `🎁 Ajak Teman (+3 Kuota & Freeze)`.
  - 1-Click Telegram Share button pre-filling an engaging invitation pitch.

---

## 🛡️ 8. Phase 8: Comprehensive QA/QC, Anti-Tamper & Security Hardening (Completed)

To ensure enterprise-grade resilience and zero vulnerabilities in financial, voice, and database flows:
* **Telegram Stars Anti-Tampering**: Strict verification of invoice payloads, currency enforcement (`XTR`), and exact Stars price validation.
* **Audio Input Guards & DoS Defense**: Enforces strict audio length limits (1s–90s) and payload size limit (max 10MB) to prevent buffer overflows and memory exhaustion.
* **SQL Injection & Schema Sanitization**: Full parameterization across all SQLite (`aiosqlite`) and PostgreSQL (`asyncpg`) queries.
* **Automated Regression Suite**: 71 comprehensive unit and integration tests passing with 0 failures.

---

## ⏳ 9. Phase 9: English Tenses Speaking Gym (`/tenses`) (Completed)

To bridge the gap between abstract grammar rules and spontaneous conversational usage:
* **Full 7-Tense Practice Catalog**:
  1. *Present Continuous*: Real-time actions & ongoing scenarios.
  2. *Simple Present*: Daily routines, habits & timeless facts.
  3. *Simple Past*: Completed historical & autobiographical events.
  4. *Past Continuous*: Interrupted past actions & narrative backdrops.
  5. *Present Perfect*: Life experiences & relevant past actions.
  6. *Future Tense (Will / Going to)*: Ambitions, predictions & organized plans.
  7. *Conditionals (If Clause Type 1 & 2)*: Realistic possibilities & hypothetical imaginations.
* **Interactive Pedagogical Flow**:
  - Interactive Formula & Concept Card.
  - On-demand Native Audio sample demonstration via `edge-tts`.
  - Concrete conversational speaking trigger scenario.
  - AI evaluation via Gemini 3.1 Flash-Lite evaluating tense accuracy (0–100%), verb inflection, and auxiliary precision.
  - Conversational spoken reply and `+25 XP` with streak progress.
* **100% Emoji UI Design**: Fully compliant zero-bullet styling for all in-chat cards and feedback messages.

## 🚀 10. Phase 10: Vercel Serverless + Neon PostgreSQL Cloud Deployment (Completed)

To achieve 100% free, 24/7 permanent cloud hosting with zero credit card requirements:
* **Vercel Serverless Webhook Adapter**: FastAPI ASGI adapter at `api/index.py` with rewrite routing via `vercel.json` and strict `X-Telegram-Bot-Api-Secret-Token` validation.
* **Neon.tech Cloud PostgreSQL**: Persistent relational storage (Singapore region) with connection pooling (`-pooler`) ensuring zero data loss and persistent user streaks/XP.
* **Dual Domain Failover Strategy**: Primary production domain (`speaking-coach-bot.tinonurcahya.dev`) with automatic fallback to `speaking-coach-bot.vercel.app`.
* **Automated Failover Watchdog & Keepalive**: Python CLI `manage_webhook.py` paired with GitHub Actions (`webhook-watchdog.yml`) scheduled every 6 hours and a 60-day auto-pause prevention script.
* **Automated Regression Suite**: 75 comprehensive unit and integration tests passing with 0 failures.

---

## 📋 11. Technical Debt & Quality Standards Registry

To preserve architectural integrity across all subsequent development cycles, engineers and agents must adhere to the following non-negotiables:

1. **Layer Boundary Enforcement**:
   - Presentation handlers (`bot/handlers/`) must never import database drivers or formulate raw SQL queries.
   - Domain services (`services/`) must remain framework-agnostic. No references to `aiogram.types.Message` or `aiogram.Bot` inside business logic.
2. **Audio File Hygiene**:
   - All voice note buffers must be handled via in-memory `io.BytesIO` streams. Never save temporary `.ogg` or `.mp3` files to disk to prevent disk saturation and container leaks.
3. **Graceful Fallbacks**:
   - External API calls (Gemini API, edge-tts) must always wrap in defensive `try/except` blocks with user-friendly Telegram error messages.
4. **Automated Testing Coverage**:
   - Every new domain service method must include corresponding unit tests under `tests/` utilizing mock repositories.
   - Maintain a minimum of 90% unit test coverage for the `services/` and `repositories/` layers.

---

## 🗓️ 12. Milestone Timeline Summary

| Milestone | Target Scope | Target Deliverable | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Baseline Clean Architecture, Gemini 2.0 Audio, TTS, Scenarios, Vocab Bank | Production-ready MVP in `apps/speaking-coach-bot` | 🟢 Completed |
| **Phase 2** | Shadowing Mode, Full IELTS 3-Part Mock Exam, Phoneme Clinic | `/shadow`, `/mock_ielts`, `/phonemes` suite | 🟢 Completed |
| **Phase 3** | Daily Streaks, Duolingo Reminders, Streak Freeze, XP & Levels 1-10, Badges, In-Chat Progress Card | Gamification engine, retention mechanics & Native Progress Card | 🟢 Completed |
| **Phase 4** | Redis Queue-Worker (Arq), PostgreSQL Migration (asyncpg), Multi-Container Topology | Auto-scaling Cloud Run & distributed worker architecture | 🟢 Completed |
| **Phase 5** | Monetization via Telegram Stars (XTR), Freemium Quota (10/day), Multi-Duration Invoices | In-chat native Stars payments, invoice & quota protection | 🟢 Completed |
| **Phase 6** | Multi-Turn Dialogue Memory (Dual Redis/DB), Contextual Roleplay Icebreakers, `/reset`, Speed Settings | Stateful 10-turn rolling memory & seamless conversation flow | 🟢 Completed |
| **Phase 7** | Referral System (`/invite`, `/referral`), Viral Growth Mechanics, Instant Rewards & Quota Boost | Deep-link invitation engine with 1-click sharing & freeze passes | 🟢 Completed |
| **Phase 8** | Comprehensive QA/QC, Anti-Tamper, Financial Security & Boundary Hardening | 75/75 automated unit & integration test coverage | 🟢 Completed |
| **Phase 9** | English Tenses Speaking Gym (`/tenses`), 7-Tense Catalog, Audio Samples & AI Evaluation | Complete interactive tenses training flow inside Telegram | 🟢 Completed |
| **Phase 10** | Vercel Serverless Adapter, Neon.tech PostgreSQL, Domain Failover Watchdog & Keepalive | 24/7 zero-cost cloud deployment with active webhook and auto-failover | 🟢 Completed |

