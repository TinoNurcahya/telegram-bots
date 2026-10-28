# 🎵 Telegram Music Discovery & Audio Downloader Bot

[![Telegram Bot](https://img.shields.io/badge/Telegram_Bot-@Musicdownloader2001__bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/Musicdownloader2001_bot)
[![Vercel Deployment](https://img.shields.io/badge/Vercel_Serverless-Live-black?style=for-the-badge&logo=vercel)](https://music-downloader-bot.tinonurcahya.dev/api/index)
[![Tests Passing](https://img.shields.io/badge/Tests-45%2F45_Passing-brightgreen?style=for-the-badge)](tests/)

> 🤖 **Coba Langsung di Telegram:** [@Musicdownloader2001_bot](https://t.me/Musicdownloader2001_bot)  
> 🌐 **Live Webhook Endpoint:** [music-downloader-bot.tinonurcahya.dev](https://music-downloader-bot.tinonurcahya.dev/api/index)

A high-performance, asynchronous Telegram Music Companion and Audio Downloader Bot built with **TypeScript (Node.js 22)**, **grammY**, **Deezer Public API**, **Apple iTunes Search API**, **LRCLIB Lyrics API**, and deployed seamlessly on **Vercel Serverless**.

---

## ✨ Fitur Unggulan

- **🔍 Pencarian Musik Cepat & Akurat (`/song <judul>`)**: Mencari lagu berdasarkan judul, nama artis, atau lirik dari katalog jutaan lagu global (Deezer & iTunes fallback).
- **📈 Tangga Lagu Terpopuler (`/charts`, `/trending`)**: Jelajahi Top 10 Global & Top 10 Indonesia secara real-time dengan tombol pemutar 1-klik.
- **🖼️ Cover Art Resolusi Tinggi (HD)**: Mengirimkan kartu lagu lengkap dengan cover album kualitas tinggi (hingga 1000x1000 px), nama album, dan durasi.
- **📥 Streaming & Unduhan Audio Telegram**: Mengirimkan file audio Telegram resmi lengkap dengan metadata (*title*, *performer*, *album art thumbnail*) secara langsung tanpa batasan payload file server.
- **🎧 Kualitas Audio 160kbps vs Studio HD 320kbps**: Pengguna Free dapat mengunduh lagu 160kbps standar, sedangkan pengguna Premium / Free Trial menikmati audio jernih Studio HD 320kbps.
- **💎 Monetisasi Telegram Stars (`XTR`) & Kuota Harian/Bulanan**: Kuota Free (5 lagu/hari, maks 50/bulan), Free Trial 7 Hari (10 lagu/hari, maks 50 lagu total), dan VIP Member (15 lagu/hari, maks 150/bulan) dengan reset harian 07:00 WIB, paket langganan Stars (25, 60, 99 Stars), dan Extra Quota Boost (+25/+50 lagu).
- **👑 Suite Khusus Admin (`/stats`, `/users`, `/broadcast`, `/grant`)**: Dashboard analitik server, pagination daftar seluruh pengguna, pesan siaran massal dengan proteksi rate limit aman (40ms) & delivery report, dan aktivasi VIP manual.
- **👥 Sistem Referral Viral (`/invite`)**: Dapatkan +3 kuota unduhan lagu tambahan untuk pengundang dan teman baru yang bergabung.
- **🎧 Pratinjau Resmi 30 Detik (Audio Preview)**: Tombol pemutar audio cuplikan resmi 30 detik untuk mendengarkan lagu secara kilat.
- **📜 Lirik Lagu Lengkap & Karaoke Timestamps (`/lyrics`)**: Integrasi langsung dengan open API **LRCLIB** untuk menampilkan lirik teks bersih dan lirik tersinkronisasi.
- **🔎 Fitur Telegram Inline Mode (`@Musicdownloader2001_bot <judul>`)**: Ketik username bot `@Musicdownloader2001_bot` langsung di chat pribadi, grup, atau channel mana saja untuk mencari dan membagikan lagu seketika ke teman.
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

Production instance bot ini beroperasi 24/7 di infrastruktur cloud serverless tanpa biaya hosting:
- 🌐 **Primary Production Domain**: [https://music-downloader-bot.tinonurcahya.dev](https://music-downloader-bot.tinonurcahya.dev)
- 🛡️ **Fallback Production Domain**: [https://music-downloader-bot.vercel.app](https://music-downloader-bot.vercel.app)
- 🤖 **Live Bot**: [@Musicdownloader2001_bot](https://t.me/Musicdownloader2001_bot)

### Langkah Setup Vercel Serverless:

1. Hubungkan repository GitHub Anda ke [Vercel](https://vercel.com).
2. Tambahkan **Environment Variables** di dashboard Vercel:
   - `BOT_TOKEN`: Token bot Anda dari BotFather
   - `DATABASE_URL`: Connection URL PostgreSQL Neon (untuk penyimpanan user & dual-key audio cache)
   - `WEBHOOK_SECRET`: Token rahasia otentikasi webhook Telegram
   - `ADMIN_ID`: Telegram User ID Admin Anda (contoh: `123456789`)
   - `RAPIDAPI_KEY`: API Key RapidAPI (`youtube-mp36`) untuk resolver lagu full
   - `NODE_ENV`: `production`
3. Daftarkan URL Webhook ke Telegram API:
   Anda dapat menggunakan Webhook Manager CLI bawaan:
   ```bash
   # Daftarkan webhook Vercel
   npm run webhook:set https://your-domain.vercel.app/api/index

   # Periksa status & kesehatan webhook di Telegram
   npm run webhook:info

   # Hapus webhook jika ingin kembali ke Long Polling lokal
   npm run webhook:delete
   ```
   *Atau gunakan perintah curl manual:*
   ```bash
   curl -F "url=https://your-domain.vercel.app/api/index" \
        -F "secret_token=your_webhook_secret" \
        https://api.telegram.org/bot<BOT_TOKEN>/setWebhook
   ```
4. Selesai! Bot Anda aktif 24/7 di Vercel secara serverless dan gratis.

