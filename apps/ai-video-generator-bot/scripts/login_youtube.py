import sys
import subprocess
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BASE_DIR = Path(__file__).resolve().parent.parent
SECRETS_FILE = BASE_DIR / "client_secrets.json"
TOKEN_FILE = BASE_DIR / "youtube_token.json"

def main():
    if not SECRETS_FILE.exists():
        print(f"❌ File tidak ditemukan: {SECRETS_FILE}", flush=True)
        return

    print("🌐 Membuka browser untuk login OAuth YouTube...", flush=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS_FILE), SCOPES)
    creds = flow.run_local_server(
        port=8080,
        prompt="consent",
        access_type="offline",
        open_browser=True,
        authorization_prompt_message="\n👉 Jika browser tidak terbuka otomatis, klik link ini:\n{url}\n"
    )

    token_json = creds.to_json()
    TOKEN_FILE.write_text(token_json, encoding="utf-8")
    print(f"\n✅ Berhasil menyimpan token baru ke: {TOKEN_FILE}", flush=True)

    try:
        subprocess.run("clip", input=token_json.encode("utf-8"), check=True)
        print("📋 Isi youtube_token.json sudah OTOMATIS TERSALIN ke Clipboard kamu (tinggal Ctrl+V)!", flush=True)
    except Exception:
        pass

    print("\n" + "=" * 70, flush=True)
    print("📋 COPY TEKS DI BAWAH INI KE GITHUB SECRET (YOUTUBE_TOKEN_JSON):", flush=True)
    print("=" * 70, flush=True)
    print(token_json, flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    main()
