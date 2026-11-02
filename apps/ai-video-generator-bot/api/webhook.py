import os
import json
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("VIDEO_GEN_BOT_TOKEN") or os.environ.get("AI_SHORTS_BOT_TOKEN") or os.environ.get("BOT_TOKEN", "")
TARGET_CHAT_ID = os.environ.get("VIDEO_GEN_TARGET_CHAT_ID") or os.environ.get("AI_SHORTS_TARGET_CHAT_ID") or os.environ.get("TARGET_CHAT_ID", "")
GH_TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", "")
GH_REPO = os.environ.get("GITHUB_REPOSITORY", "TinoNurcahya/telegram-bots")

def send_telegram_message(chat_id: int, text: str, reply_markup: dict = None) -> bool:
    """Sends a fast markdown message to Telegram via Bot API HTTP request."""
    if not BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

def trigger_github_action(topic: str = "") -> bool:
    """Triggers GitHub Actions repository_dispatch event to start video rendering."""
    if not GH_TOKEN:
        print("GH_TOKEN is not configured.")
        return False

    url = f"https://api.github.com/repos/{GH_REPO}/dispatches"
    payload = {
        "event_type": "generate-video",
        "client_payload": {
            "topic": topic
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Shorts-Studio-Webhook"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status in (200, 204)
    except Exception as e:
        print(f"Error triggering GitHub Action: {e}")
        return False

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "online",
            "service": "AI Shorts Studio Webhook Bridge",
            "repo": GH_REPO
        }).encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            update = json.loads(post_data.decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        # Handle Message
        message = update.get("message")
        if message:
            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")
            text = (message.get("text") or "").strip()

            if text.startswith("/start"):
                welcome_text = (
                    "🎬 *Selamat Datang di AI Shorts Studio!* ⚡\n\n"
                    "Studio produksi video vertikal 9:16 otomatis dengan narasi Female English Natural profesional.\n\n"
                    "🔹 `/generate [topik opsional]` — Memulai pembuatan video Shorts.\n"
                    "🔹 `/status` — Memeriksa status pipeline dan engine render.\n"
                    "🔹 `/help` — Panduan penggunaan bot.\n\n"
                    "💡 *Ketik `/generate` untuk langsung membuat video misteri/sains otomatis!*"
                )
                send_telegram_message(chat_id, welcome_text)

            elif text.startswith("/help"):
                help_text = (
                    "📖 *Panduan Penggunaan AI Shorts Studio*\n\n"
                    "1. Ketik `/generate` untuk membuat video dengan topik 100% acak.\n"
                    "2. Ketik `/generate Rahasia Piramida Giza` untuk topik spesifik.\n"
                    "3. Pipeline akan merender video di cloud engine 16GB RAM dan mengirim hasilnya langsung ke chat ini!"
                )
                send_telegram_message(chat_id, help_text)

            elif text.startswith("/status"):
                status_text = (
                    "⚙️ *Status Sistem AI Shorts Studio*\n\n"
                    "🟢 *Webhook Bridge*: Aktif (Vercel Serverless)\n"
                    "🚀 *Render Engine*: GitHub Actions (4 vCPU / 16 GB RAM)\n"
                    "⏰ *Jadwal Harian*: Setiap 08:00 WIB (Asia/Jakarta)\n"
                    f"🆔 *Chat ID Anda*: `{chat_id}`"
                )
                send_telegram_message(chat_id, status_text)

            elif text.startswith("/generate"):
                # Admin Access Verification
                if TARGET_CHAT_ID and str(TARGET_CHAT_ID) != "0":
                    if str(user_id) != str(TARGET_CHAT_ID) and str(chat_id) != str(TARGET_CHAT_ID):
                        send_telegram_message(
                            chat_id,
                            "⛔ *Akses Ditolak*\n\nBot ini beroperasi sebagai Studio Pribadi. "
                            "Perintah pembuatan video hanya diizinkan untuk Admin Studio terdaftar."
                        )
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b"OK")
                        return

                parts = text.split(maxsplit=1)
                custom_topic = parts[1].strip() if len(parts) > 1 else ""

                topic_desc = f"*\"{custom_topic}\"*" if custom_topic else "*Acak (15+ Kategori Misteri & Sains)*"
                notify_msg = (
                    "🎬 *Studio Video AI Dimulai!*\n\n"
                    f"📌 Topik: {topic_desc}\n"
                    "⚡ Permintaan sedang dikirim ke Render Engine (GitHub Actions 16GB RAM).\n"
                    "⏳ Video, thumbnail, dan link YouTube akan otomatis dikirim ke sini dalam ~1–2 menit!"
                )
                send_telegram_message(chat_id, notify_msg)

                # Trigger the heavyweight GitHub Action
                success = trigger_github_action(topic=custom_topic)
                if not success:
                    send_telegram_message(
                        chat_id,
                        "⚠️ *Gagal memicu Render Engine.*\nPastikan `GH_PAT` telah dikonfigurasi di Environment Variables Vercel."
                    )

        # Handle Callback Query
        callback_query = update.get("callback_query")
        if callback_query:
            cb_chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
            cb_user_id = callback_query.get("from", {}).get("id")
            cb_data = callback_query.get("data", "")

            if cb_data in ("btn:generate_instant", "btn:generate_prompt") or cb_data.startswith("gen_topic:"):
                if TARGET_CHAT_ID and str(TARGET_CHAT_ID) != "0":
                    if str(cb_user_id) != str(TARGET_CHAT_ID) and str(cb_chat_id) != str(TARGET_CHAT_ID):
                        send_telegram_message(cb_chat_id, "⛔ Akses Khusus Admin Studio.")
                    else:
                        notify_msg = (
                            "🎬 *Studio Video AI Dimulai!*\n\n"
                            "🎲 Memilih topik misteri & sains secara acak...\n"
                            "⚡ Permintaan sedang diproses di Render Engine (16GB RAM). Harap tunggu ~1–2 menit!"
                        )
                        send_telegram_message(cb_chat_id, notify_msg)
                        trigger_github_action(topic="")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
