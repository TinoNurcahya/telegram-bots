import os
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

    def is_configured(self) -> bool:
        """Checks if YouTube OAuth credentials file exists."""
        return self.credentials_storage.exists() or self.client_secrets_file.exists()

    def get_authenticated_service(self):
        """Builds YouTube Data API client from stored credentials."""
        if not Credentials:
            raise RuntimeError("Google API Client libraries are not installed.")

        # Check if token JSON is provided directly via environment variable
        env_token = os.environ.get("YOUTUBE_TOKEN_JSON")
        if env_token and not self.credentials_storage.exists():
            try:
                self.credentials_storage.parent.mkdir(parents=True, exist_ok=True)
                with open(self.credentials_storage, "w", encoding="utf-8") as f:
                    f.write(env_token)
                logger.info("Restored YouTube token from YOUTUBE_TOKEN_JSON environment variable.")
            except Exception as e:
                logger.warning(f"Failed to write YOUTUBE_TOKEN_JSON to file: {e}")

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
        privacy_status: str = "public"
    ) -> Optional[str]:
        """
        Uploads .mp4 video to YouTube Shorts and sets custom thumbnail if provided.
        Returns YouTube video ID if successful, or None if credentials not configured.
        """
        if not self.is_configured():
            logger.warning("YouTube credentials not configured. Skipping automated upload.")
            return None

        youtube = self.get_authenticated_service()
        if not youtube:
            logger.warning("Could not authenticate with YouTube.")
            return None

        body = {
            "snippet": {
                "title": title[:100],
                "description": f"{description}\n\n#shorts #viral",
                "tags": tags,
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
                logger.info(f"YouTube upload progress: {int(status.progress() * 100)}%")

        video_id = response.get("id")
        logger.info(f"Successfully uploaded to YouTube: https://youtube.com/shorts/{video_id}")

        # Set custom thumbnail if provided and supported
        if video_id and thumbnail_path and os.path.exists(thumbnail_path):
            try:
                thumb_media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")
                youtube.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
                logger.info(f"Custom thumbnail successfully set for YouTube video {video_id}")
            except Exception as te:
                logger.warning(f"Could not set custom thumbnail via YouTube API (channel may need phone verification): {te}")

        return video_id
