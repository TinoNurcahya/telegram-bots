import os
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    build = None
    MediaFileUpload = None
    Credentials = None
    InstalledAppFlow = None

from src.config import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class YouTubeService:
    def __init__(
        self,
        client_secrets_file: Optional[str] = None,
        credentials_storage: Optional[str] = None
    ):
        base = Path(__file__).resolve().parent.parent.parent
        self.client_secrets_file = base / (client_secrets_file or settings.YOUTUBE_CLIENT_SECRETS_FILE)
        self.credentials_storage = base / (credentials_storage or settings.YOUTUBE_CREDENTIALS_STORAGE)
        self.last_error: Optional[str] = None
        self._ensure_token_restored()

    def _ensure_token_restored(self):
        """Restores youtube_token.json from YOUTUBE_TOKEN_JSON environment variable if available."""
        env_token = (os.environ.get("YOUTUBE_TOKEN_JSON") or "").strip()
        if env_token and not self.credentials_storage.exists():
            try:
                self.credentials_storage.parent.mkdir(parents=True, exist_ok=True)
                with open(self.credentials_storage, "w", encoding="utf-8") as f:
                    f.write(env_token)
                logger.info("Restored YouTube token from YOUTUBE_TOKEN_JSON environment variable.")
            except Exception as e:
                logger.warning(f"Failed to write YOUTUBE_TOKEN_JSON to file: {e}")

    def is_configured(self) -> bool:
        """Checks if YouTube OAuth credentials exist (file or environment variable)."""
        self._ensure_token_restored()
        return (
            bool(os.environ.get("YOUTUBE_TOKEN_JSON"))
            or self.credentials_storage.exists()
            or self.client_secrets_file.exists()
        )

    def get_authenticated_service(self):
        """Builds YouTube Data API client from stored credentials."""
        if not Credentials:
            raise RuntimeError("Google API Client libraries are not installed.")

        self._ensure_token_restored()

        creds = None
        if self.credentials_storage.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.credentials_storage), SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load YouTube credentials from storage: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    from google.auth.transport.requests import Request
                    creds.refresh(Request())
                    try:
                        with open(self.credentials_storage, "w", encoding="utf-8") as token_file:
                            token_file.write(creds.to_json())
                    except Exception:
                        pass
                    logger.info("YouTube OAuth access token successfully refreshed.")
                except Exception as re:
                    err_str = str(re).lower()
                    if "invalid_grant" in err_str:
                        self.last_error = "Token otorisasi YouTube kadaluarsa atau dicabut (invalid_grant). Perbarui YOUTUBE_TOKEN_JSON."
                    else:
                        self.last_error = f"Gagal me-refresh token YouTube: {str(re)[:120]}"
                    logger.warning(f"Could not refresh YouTube token, will re-authenticate: {re}")
                    creds = None

            if not creds or not creds.valid:
                # In headless CI/CD environments (GitHub Actions / Docker), do not attempt interactive browser flow
                is_headless = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS") or not os.isatty(0) if hasattr(os, "isatty") else False)
                if self.client_secrets_file.exists() and not is_headless:
                    logger.info("Initializing OAuth flow for YouTube...")
                    flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secrets_file), SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(self.credentials_storage, "w", encoding="utf-8") as token_file:
                        token_file.write(creds.to_json())
                else:
                    logger.warning("YouTube credentials not available or expired in headless environment. Skipping YouTube upload.")
                    return None

        return build("youtube", "v3", credentials=creds)

    async def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: List[str],
        thumbnail_path: Optional[Path] = None,
        privacy_status: str = "public",
        is_short: bool = True
    ) -> Optional[str]:
        """
        Uploads .mp4 video to YouTube (Shorts or 16:9 Long-Form) with automatic 3x retry on transient failures.
        Sets self.last_error if upload fails for transparent user feedback.
        """
        self.last_error = None
        if not self.is_configured():
            self.last_error = "Kredensial YouTube belum dikonfigurasi (file client_secrets.json atau token tidak ditemukan)."
            logger.warning(self.last_error)
            return None

        def _do_upload() -> Optional[str]:
            max_attempts = 3
            backoff_delays = [3, 6, 12]

            for attempt in range(1, max_attempts + 1):
                try:
                    youtube = self.get_authenticated_service()
                    if not youtube:
                        if not self.last_error:
                            self.last_error = "Gagal mengautentikasi kredensial YouTube."
                        logger.warning(self.last_error)
                        return None

                    desc_hashtags = "#shorts #viral" if is_short else "#documentary #mystery #science"
                    clean_tags = tags if is_short else [t for t in tags if "short" not in t.lower()]
                    body = {
                        "snippet": {
                            "title": title[:100],
                            "description": f"{description}\n\n{desc_hashtags}",
                            "tags": clean_tags,
                            "categoryId": "27"  # Education
                        },
                        "status": {
                            "privacyStatus": privacy_status,
                            "selfDeclaredMadeForKids": False
                        }
                    }

                    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
                    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

                    response = None
                    while response is None:
                        status, response = request.next_chunk()
                        if status:
                            logger.info(f"YouTube upload progress (attempt {attempt}): {int(status.progress() * 100)}%")

                    v_id = response.get("id")
                    yt_link = f"https://youtube.com/shorts/{v_id}" if is_short else f"https://youtube.com/watch?v={v_id}"
                    logger.info(f"Successfully uploaded to YouTube: {yt_link}")

                    # Set custom thumbnail if provided and supported
                    if v_id and thumbnail_path and os.path.exists(thumbnail_path):
                        try:
                            thumb_media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
                            youtube.thumbnails().set(videoId=v_id, media_body=thumb_media).execute()
                            logger.info(f"Custom thumbnail successfully set for YouTube video {v_id}")
                        except Exception as te:
                            logger.warning(f"Could not set custom thumbnail via YouTube API: {te}")

                    self.last_error = None
                    return v_id

                except Exception as e:
                    err_msg = str(e).lower()
                    logger.error(f"YouTube upload attempt {attempt}/{max_attempts} failed: {e}")

                    # Non-retryable errors
                    if "quotaexceeded" in err_msg:
                        self.last_error = "Kuota harian YouTube Data API (10.000 unit) telah habis untuk hari ini."
                        break
                    if "uploadlimitexceeded" in err_msg:
                        self.last_error = "Batas upload harian channel YouTube tercapai."
                        break
                    if "invalid_grant" in err_msg:
                        self.last_error = "Token otorisasi YouTube kadaluarsa. Perlu login ulang."
                        break

                    if attempt < max_attempts:
                        delay = backoff_delays[attempt - 1]
                        logger.info(f"Retrying YouTube upload in {delay}s...")
                        time.sleep(delay)
                    else:
                        self.last_error = f"Gagal upload setelah 3x percobaan: {str(e)[:120]}"

            return None

        return await asyncio.to_thread(_do_upload)
