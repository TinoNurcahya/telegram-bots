from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Returns a persistent bottom reply keyboard with direct 1-tap action buttons
    so users don't need to type '/' commands manually.
    """
    keyboard = [
        [
            KeyboardButton(text="🎬 Generate Video (1-Click)"),
        ],
        [
            KeyboardButton(text="🔍 Kategori Kasus"),
            KeyboardButton(text="📊 Statistik"),
        ],
        [
            KeyboardButton(text="⚙️ Status Sistem"),
            KeyboardButton(text="📖 Panduan"),
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Pilih menu atau ketik /..."
    )
