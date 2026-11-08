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
    """Returns interactive categories selection keyboard."""
    return get_categories_keyboard()

def get_categories_keyboard() -> InlineKeyboardMarkup:
    """Displays the 15 investigative/analytical categories with compact callback keys."""
    CATEGORY_LABELS = [
        "🧠 Dark Psychology",
        "🕵️ Classified Enigmas",
        "📜 Unsolved Mysteries",
        "💥 What If? Scenarios",
        "🌌 Cosmic Paradoxes",
        "🌊 Deep Oceans & Nature",
        "🔍 Forensic Deduction",
        "🌀 Reality Glitches",
        "🌋 Forbidden Terrains",
        "🏛️ Lost Civilizations",
        "⚛️ Quantum Paradoxes",
        "🤯 Bizarre Facts",
        "🧬 Brain Curiosities",
        "⏳ Time Paradoxes",
        "🔐 Cryptic Codes"
    ]

    buttons = []
    # Build 2-column keyboard for compact layout
    row = []
    for idx, label in enumerate(CATEGORY_LABELS):
        row.append(InlineKeyboardButton(text=label, callback_data=f"pick_cat:{idx}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="🎲 Kasus Acak (1-Click Random)", callback_data="btn:generate_instant"),
        InlineKeyboardButton(text="🏠 Menu Utama", callback_data="btn:main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_category_topics_keyboard(cat_idx: int, cat_name: str, angles: List[str]) -> InlineKeyboardMarkup:
    """Displays topics under the selected category."""
    buttons = []
    for t_idx, topic in enumerate(angles):
        short_topic = topic[:42] + "..." if len(topic) > 42 else topic
        buttons.append([
            InlineKeyboardButton(text=f"🎬 {short_topic}", callback_data=f"gen_topic:{cat_idx}:{t_idx}")
        ])

    buttons.append([
        InlineKeyboardButton(text="🔙 Pilih Kategori Lain", callback_data="btn:topics_menu"),
        InlineKeyboardButton(text="🏠 Menu Utama", callback_data="btn:main_menu")
    ])
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
            InlineKeyboardButton(text="🔄 Coba Upload ke YouTube Lagi", callback_data=f"yt_upload:{video_id}")
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

