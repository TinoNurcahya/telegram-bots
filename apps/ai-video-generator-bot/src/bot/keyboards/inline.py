from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Optional

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Returns the main interactive inline keyboard with 1-click instant generation."""
    buttons = [
        [
            InlineKeyboardButton(text="🎬 Generate AI Short (1-Click Random Case)", callback_data="btn:generate_instant"),
        ],
        [
            InlineKeyboardButton(text="📊 Riwayat & Statistik", callback_data="btn:stats"),
            InlineKeyboardButton(text="⚙️ Info Sistem", callback_data="btn:system_info"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_topic_selection_keyboard(topics: Optional[List[str]] = None) -> InlineKeyboardMarkup:
    """Fallback keyboard allowing immediate random generation or returning home."""
    buttons = [
        [
            InlineKeyboardButton(text="🎲 Generate Kasus Acak Sekarang", callback_data="btn:generate_instant"),
        ],
        [
            InlineKeyboardButton(text="🔙 Menu Utama", callback_data="btn:main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_video_actions_keyboard(video_id: int, youtube_id: Optional[str] = None, has_youtube_id: bool = False) -> InlineKeyboardMarkup:
    """Displays action buttons below a freshly generated video."""
    buttons = []
    yt_id = youtube_id if youtube_id else None
    if yt_id:
        buttons.append([
            InlineKeyboardButton(text="▶️ Tonton di YouTube Shorts", url=f"https://youtube.com/shorts/{yt_id}")
        ])
    elif not has_youtube_id:
        buttons.append([
            InlineKeyboardButton(text="🚀 Upload ke YouTube Shorts", callback_data=f"yt_upload:{video_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="✅ Sudah Terupload di YouTube", callback_data="noop")
        ])

    buttons.append([
        InlineKeyboardButton(text="🎬 Buat Video Baru (Random Case)", callback_data="btn:generate_instant"),
        InlineKeyboardButton(text="🏠 Menu Utama", callback_data="btn:main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_tts_retry_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown when Google AI Studio TTS quota limit is reached."""
    buttons = [
        [
            InlineKeyboardButton(text="🔄 Coba Lagi", callback_data="btn:generate_instant"),
            InlineKeyboardButton(text="🏠 Menu Utama", callback_data="btn:main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

