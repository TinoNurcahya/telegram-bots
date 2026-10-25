try:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
except ImportError:
    class InlineKeyboardButton:  # type: ignore
        def __init__(self, text: str = "", callback_data: str = "", url: str = "", web_app=None, **kwargs):
            self.text = text
            self.callback_data = callback_data
            self.url = url
            self.web_app = web_app

    class InlineKeyboardMarkup:  # type: ignore
        def __init__(self, inline_keyboard=None, **kwargs):
            self.inline_keyboard = inline_keyboard or []

    class WebAppInfo:  # type: ignore
        def __init__(self, url: str = "", **kwargs):
            self.url = url

import urllib.parse
from src.services.tts_service import AVAILABLE_VOICES, SPEED_PRESETS


def get_main_menu_keyboard(tma_url: str = "") -> InlineKeyboardMarkup:
    """Primary navigation menu for Speaking Coach (100% Native Telegram)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎓 IELTS Mock Exam (/mock_ielts)", callback_data="btn_start_mock_ielts"),
            ],
            [
                InlineKeyboardButton(text="🎧 Shadowing Mode (/shadow)", callback_data="btn_start_shadow"),
                InlineKeyboardButton(text="👄 Latihan Fonem (/phonemes)", callback_data="btn_open_phonemes"),
            ],
            [
                InlineKeyboardButton(text="⏳ Klinik Tenses (/tenses)", callback_data="btn_open_tenses"),
                InlineKeyboardButton(text="📊 Statistik & Progres (/progress)", callback_data="btn_my_progress"),
            ],
            [
                InlineKeyboardButton(text="⭐ Upgrade Premium", callback_data="buy_premium"),
                InlineKeyboardButton(text="🎁 Ajak Teman (+3 Kuota & Freeze)", callback_data="open_referral_menu"),
            ],
            [
                InlineKeyboardButton(text="⏰ Pengingat (/remind)", callback_data="remind_settings"),
            ],
            [
                InlineKeyboardButton(text="🎭 Roleplay Scenarios", callback_data="btn_open_scenarios"),
                InlineKeyboardButton(text="💡 Get Topic", callback_data="btn_get_topic"),
            ],
            [
                InlineKeyboardButton(text="🎯 Target Level", callback_data="btn_select_level"),
                InlineKeyboardButton(text="📖 Vocab Bank (/review)", callback_data="btn_vocab_review"),
            ],
            [
                InlineKeyboardButton(text="🎙️ Suara AI (/voice)", callback_data="btn_voice_settings"),
                InlineKeyboardButton(text="⚡ Kecepatan Suara (/speed)", callback_data="open_speed_settings"),
            ],
        ]
    )


def get_progress_navigation_keyboard() -> InlineKeyboardMarkup:
    """Interactive navigation bar for the 100% Native Telegram progress card."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Refresh Data", callback_data="btn_refresh_progress"),
                InlineKeyboardButton(text="📖 Vocab Bank (/review)", callback_data="btn_vocab_review"),
            ],
            [
                InlineKeyboardButton(text="🎯 Ganti Target (/level)", callback_data="btn_select_level"),
                InlineKeyboardButton(text="🎭 Ganti Skenario (/scenario)", callback_data="btn_open_scenarios"),
            ],
            [
                InlineKeyboardButton(text="🔙 Menu Utama", callback_data="btn_back_main"),
            ],
        ]
    )


def get_referral_keyboard(referral_link: str, share_text: str = "") -> InlineKeyboardMarkup:
    """Keyboard for sharing referral link with 1-click Telegram share button."""
    encoded_text = urllib.parse.quote(share_text)
    encoded_link = urllib.parse.quote(referral_link)
    share_url = f"https://t.me/share/url?url={encoded_link}&text={encoded_text}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Bagikan ke Teman / Grup",
                    url=share_url,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Kembali ke Menu Utama",
                    callback_data="back_to_main",
                ),
            ],
        ]
    )


def get_freemium_limit_keyboard(has_used_trial: bool = False) -> InlineKeyboardMarkup:
    """Keyboard shown when a free user exhausts their daily quota."""
    rows = []
    if not has_used_trial:
        rows.append([
            InlineKeyboardButton(
                text="🎁 Klaim 7 Hari Trial Gratis",
                callback_data="claim_trial_7d",
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text="⭐ Upgrade ke Premium (Pilihan Paket Stars)",
            callback_data="buy_premium",
        )
    ])
    rows.append([
        InlineKeyboardButton(
            text="📊 Cek Statistik & XP (/progress)",
            callback_data="btn_my_progress",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_upgrade_keyboard(has_used_trial: bool = False, is_active_subscriber: bool = False) -> InlineKeyboardMarkup:
    """Keyboard for payment packages and free trial."""
    buttons = []

    # 1. Free Trial button (only if user hasn't claimed it yet)
    if not has_used_trial and not is_active_subscriber:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🎁 Klaim 7 Hari Trial Gratis",
                    callback_data="claim_trial_7d",
                )
            ]
        )

    # 2. Duration packages
    buttons.append(
        [
            InlineKeyboardButton(
                text="🌟 1 Bulan — 40 Stars",
                callback_data="pay_stars_1m",
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="🚀 3 Bulan — 95 Stars (Hemat 20%)",
                callback_data="pay_stars_3m",
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="👑 Seumur Hidup — 150 Stars",
                callback_data="pay_stars_lifetime",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reminder_menu_keyboard(current_time: str = "20:00", is_enabled: bool = True) -> InlineKeyboardMarkup:
    """Settings menu for proactive daily streak reminders."""
    status_text = "🔔 Status: AKTIF (Tekan utk Matikan)" if is_enabled else "🔕 Status: NONAKTIF (Tekan utk Aktifkan)"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=status_text, callback_data="remind_toggle"),
            ],
            [
                InlineKeyboardButton(text="🌅 Pagi (08:00)", callback_data="remind_set:08:00"),
                InlineKeyboardButton(text="☀️ Siang (13:00)", callback_data="remind_set:13:00"),
            ],
            [
                InlineKeyboardButton(text="🌙 Malam (20:00)", callback_data="remind_set:20:00"),
                InlineKeyboardButton(text="⚙️ Jam Lain", callback_data="remind_custom_prompt"),
            ],
            [
                InlineKeyboardButton(text="🧪 Uji Notifikasi Sekarang", callback_data="remind_test_now"),
            ],
        ]
    )


def get_reminder_action_keyboard() -> InlineKeyboardMarkup:
    """Action buttons attached to proactive reminder messages."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎙️ Bicara Sekarang", callback_data="btn_open_scenarios"),
                InlineKeyboardButton(text="🎧 Shadowing", callback_data="btn_start_shadow"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Atur Jam Pengingat", callback_data="remind_settings"),
            ],
        ]
    )


def get_ielts_exam_type_keyboard() -> InlineKeyboardMarkup:
    """Selection keyboard for IELTS Mock Exam duration."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ Express Exam (3 Soal, ~4 Menit)",
                    callback_data="ielts_start:express",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏛️ Full Simulation (6 Soal, ~12 Menit)",
                    callback_data="ielts_start:full",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Batal",
                    callback_data="ielts_cancel",
                )
            ],
        ]
    )


def get_ielts_question_keyboard(step_index: int) -> InlineKeyboardMarkup:
    """Controls for an in-progress IELTS blind listening question."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👁️ Tampilkan Teks Pertanyaan",
                    callback_data=f"ielts_reveal:{step_index}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Batalkan Ujian",
                    callback_data="ielts_cancel",
                )
            ],
        ]
    )


def get_ielts_cue_card_keyboard() -> InlineKeyboardMarkup:
    """Controls for Part 2 Cue Card preparation and recording."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎙️ Saya Siap Rekam Monolog (1-2 Menit)",
                    callback_data="ielts_ready_cue",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Batalkan Ujian",
                    callback_data="ielts_cancel",
                )
            ],
        ]
    )



def get_shadowing_control_keyboard() -> InlineKeyboardMarkup:
    """Controls for active Shadowing exercise."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Another Sentence", callback_data="btn_start_shadow"),
                InlineKeyboardButton(text="❌ End Shadowing", callback_data="btn_cancel_shadow"),
            ]
        ]
    )


def get_level_selection_keyboard(current_level: str = "Intermediate") -> InlineKeyboardMarkup:
    """Keyboard to choose language proficiency level."""
    levels = [
        ("🟢 Beginner (A1 - A2)", "lvl_Beginner"),
        ("🟡 Intermediate (B1 - B2)", "lvl_Intermediate"),
        ("🔴 Advanced (C1 - C2)", "lvl_Advanced"),
    ]

    buttons = []
    for label, callback in levels:
        is_active = "✓ " if current_level in label else ""
        buttons.append([InlineKeyboardButton(text=f"{is_active}{label}", callback_data=callback)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_scenario_selection_keyboard(current_scenario: str = "Free Conversation") -> InlineKeyboardMarkup:
    """Keyboard to select a roleplay simulation scenario."""
    scenarios = [
        ("🗣️ Free Casual Conversation", "scen_Free Conversation"),
        ("💼 Job Interview Simulation", "scen_Job Interview"),
        ("☕ Cafe & Ordering Food", "scen_Cafe & Dining"),
        ("✈️ Airport & Immigration", "scen_Airport Immigration"),
        ("🏢 Tech Team Daily Standup", "scen_Tech Standup"),
    ]

    buttons = []
    for label, callback in scenarios:
        active_tag = "✓ " if callback.replace("scen_", "") == current_scenario else ""
        buttons.append([InlineKeyboardButton(text=f"{active_tag}{label}", callback_data=callback)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_voice_selection_keyboard(current_voice: str = "en-US-JennyNeural") -> InlineKeyboardMarkup:
    """Keyboard to pick the AI's spoken reply voice."""
    buttons = []
    for label, voice_id in AVAILABLE_VOICES.items():
        is_active = "✓ " if voice_id == current_voice else ""
        buttons.append([InlineKeyboardButton(text=f"{is_active}{label}", callback_data=f"voice_{voice_id}")])

    buttons.append([
        InlineKeyboardButton(text="⚡ Atur Kecepatan Suara (/speed)", callback_data="open_speed_settings")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_speed_selection_keyboard(current_speed: str = "+0%") -> InlineKeyboardMarkup:
    """Keyboard to pick the AI's spoken speech rate."""
    buttons = []
    for key, item in SPEED_PRESETS.items():
        is_active = "✓ " if item["rate"] == current_speed else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{is_active}{item['label']}",
                callback_data=f"speed_{item['rate']}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="🎙️ Ganti Aksen Suara (/voice)", callback_data="btn_voice_settings"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_phoneme_categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Keyboard displaying all minimal pair categories + random button."""
    buttons = []
    for cat in categories:
        cat_id = cat["id"]
        title = cat["title"]
        buttons.append([InlineKeyboardButton(text=title, callback_data=f"phoneme_cat:{cat_id}")])

    buttons.append([
        InlineKeyboardButton(text="🎲 Latihan Pasangan Acak", callback_data="phoneme_random")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_phoneme_pairs_keyboard(category_id: str, pairs: list) -> InlineKeyboardMarkup:
    """Keyboard listing available minimal pairs within a selected category."""
    buttons = []
    for p in pairs:
        pair_id = p["id"]
        label = f"🎯 {p['word_a']} vs {p['word_b']} ({p['ipa_a']} vs {p['ipa_b']})"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"phoneme_drill:{pair_id}")])

    buttons.append([
        InlineKeyboardButton(text="« Kembali ke Kategori", callback_data="btn_open_phonemes"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_phoneme_drill_keyboard(pair_id: str) -> InlineKeyboardMarkup:
    """Interactive control keyboard for active minimal pair drill."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎧 Dengarkan Contoh Pengucapan",
                    callback_data=f"phoneme_audio:{pair_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Batalkan Latihan",
                    callback_data="phoneme_cancel",
                )
            ],
        ]
    )


def get_phoneme_result_keyboard(pair_id: str, category_id: str) -> InlineKeyboardMarkup:
    """Next action buttons after receiving phoneme feedback scorecard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Coba Lagi Pasangan Ini",
                    callback_data=f"phoneme_drill:{pair_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="➡️ Pasangan Lain di Kategori Ini",
                    callback_data=f"phoneme_cat:{category_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👄 Menu Utama Fonem",
                    callback_data="btn_open_phonemes",
                ),
            ],
        ]
    )


def get_tenses_selection_keyboard() -> InlineKeyboardMarkup:
    """Return inline buttons for selecting one of the 7 English Tenses drills."""
    from src.services.ai_coach_service import get_tenses_catalog
    catalog = get_tenses_catalog()

    buttons = []
    for tense_id, item in catalog.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{item['icon']} {item['title']}",
                callback_data=f"tense_drill:{tense_id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="🔙 Menu Utama", callback_data="btn_back_main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_tense_card_keyboard(tense_id: str) -> InlineKeyboardMarkup:
    """Control keyboard for active tense exercise card."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔊 Dengarkan Contoh Audio",
                    callback_data=f"tense_audio:{tense_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Ganti Kategori Tenses",
                    callback_data="btn_open_tenses",
                ),
                InlineKeyboardButton(
                    text="❌ Batalkan",
                    callback_data="tense_cancel",
                ),
            ],
        ]
    )


def get_tense_result_keyboard(tense_id: str) -> InlineKeyboardMarkup:
    """Follow-up keyboard after tense exercise feedback."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Latihan Lagi Tenses Ini",
                    callback_data=f"tense_drill:{tense_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏳ Pilih Tenses Lain",
                    callback_data="btn_open_tenses",
                ),
                InlineKeyboardButton(
                    text="🔙 Menu Utama",
                    callback_data="btn_back_main",
                ),
            ],
        ]
    )

