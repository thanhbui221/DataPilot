"""Telegram bot keyboard layouts."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_run_decision_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for SQL execution decision."""
    keyboard = [
        [
            InlineKeyboardButton("▶️ Run query", callback_data="run_query"),
            InlineKeyboardButton("🧾 Show SQL only", callback_data="show_sql")
        ],
        [
            InlineKeyboardButton("✏️ Modify SQL", callback_data="modify_sql"),
            InlineKeyboardButton("🔄 Modify intent", callback_data="modify_intent")
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_intent_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for intent confirmation."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_intent"),
            InlineKeyboardButton("✏️ Modify", callback_data="modify_intent")
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

