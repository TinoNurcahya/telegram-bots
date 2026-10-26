# 🎵 Telegram Music Discovery & Audio Downloader Bot

A high-performance, asynchronous Telegram Music Companion and Audio Downloader Bot built with **TypeScript (Node.js 22)**, **grammY**, **Deezer Public API**, **Apple iTunes Search API**, **LRCLIB Lyrics API**, and deployed seamlessly on **Vercel Serverless**.

---

## ✨ Fitur Unggulan

- **🔍 Pencarian Musik Cepat & Akurat (`/song <judul>`)**: Mencari lagu berdasarkan judul, nama artis, atau lirik dari katalog jutaan lagu global (Deezer & iTunes fallback).
- **🖼️ Cover Art Resolusi Tinggi (HD)**: Mengirimkan kartu lagu lengkap dengan cover album kualitas tinggi (hingga 1000x1000 px), nama album, dan durasi.
- **📥 Streaming & Unduhan Audio Telegram**: Mengirimkan file audio Telegram resmi lengkap dengan metadata (*title*, *performer*, *album art thumbnail*) secara langsung tanpa batasan payload file server.
- **🎧 Pratinjau Resmi 30 Detik (Audio Preview)**: Tombol pemutar audio cuplikan resmi 30 detik untuk mendengarkan lagu secara kilat.
- **📜 Lirik Lagu Lengkap & Karaoke Timestamps (`/lyrics`)**: Integrasi langsung dengan open API **LRCLIB** untuk menampilkan lirik teks bersih dan lirik tersinkronisasi.
- **🔎 Fitur Telegram Inline Mode (`@NamaBot <judul>`)**: Ketik username bot langsung di chat pribadi, grup, atau channel mana saja untuk mencari dan membagikan lagu seketika ke teman.
- **⚡ Arsitektur Serverless Vercel**: Sub-100ms response time, zero maintenance server, dan bebas biaya hosting selamanya.

---

## 🏛️ Struktur Proyek

```
music-downloader-bot/
├── api/
│   └── index.ts                 # ⚡ Vercel Serverless Webhook Adapter (grammY)
├── src/
│   ├── bot/
│   │   ├── handlers/
│   │   │   ├── music.handler.ts # /song, /start, /help, text search, download & lyrics callbacks
│   │   │   └── inline.handler.ts# @botname inline search across chats
│   │   ├── keyboards/
│   │   │   └── player.keyboard.ts # Inline player buttons & pagination controls
│   │   └── bot.ts               # Inisialisasi bot & dependency injection
│   ├── services/
│   │   ├── music.service.ts     # Deezer, iTunes, and JioSaavn audio stream resolvers
│   │   └── lyrics.service.ts    # LRCLIB lyrics provider & formatters
│   ├── config/
│   │   └── env.ts               # Environment validation (BOT_TOKEN, WEBHOOK_SECRET)
│   ├── types/
│   │   └── music.ts             # TypeScript interfaces
│   └── main.ts                  # Local Long Polling runner (npm run dev)
├── tests/                       # Unit & integration test suite (Vitest)
├── package.json
├── tsconfig.json
├── vercel.json
├── .env.example
└── README.md
```

---

## 🚀 Panduan Menjalankan Bot

### 1. Setup Dependensi
Pastikan Node.js v20+ atau v22+ telah terinstall di sistem Anda:
```bash
npm install
```

### 2. Konfigurasi Lingkungan (`.env`)
Salin file `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```
Isi `BOT_TOKEN` yang Anda dapatkan dari [@BotFather](https://t.me/BotFather):
```env
BOT_TOKEN=123456789:ABCDefGhIJKlmNoPQRstuVWXyz
WEBHOOK_SECRET=my_custom_secure_secret_token
```

### 3. Jalankan Mode Development (Local Long Polling)
```bash
npm run dev
```

### 4. Eksekusi Unit Test Suite
```bash
npm test
```

### 5. Kompilasi TypeScript
```bash
npm run build
```

---

## 🌐 Panduan Deployment Vercel Serverless

1. Hubungkan repository GitHub Anda ke [Vercel](https://vercel.com).
2. Tambahkan **Environment Variables** di dashboard Vercel:
   - `BOT_TOKEN`: Token bot Anda dari BotFather
   - `WEBHOOK_SECRET`: Token rahasia webhook
3. Daftarkan URL Webhook ke Telegram API:
   ```bash
   curl -F "url=https://your-domain.vercel.app/api/index" \
        -F "secret_token=your_webhook_secret" \
        https://api.telegram.org/bot<BOT_TOKEN>/setWebhook
   ```
4. Selesai! Bot Anda aktif 24/7 di Vercel secara gratis.
