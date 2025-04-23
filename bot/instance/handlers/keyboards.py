from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import BOT_USERNAME
# Inline tugma yaratish
add_group_inline_button = InlineKeyboardButton(
    text="➕ Guruhga qo‘shish ➕",
    url=f"https://t.me/{BOT_USERNAME}?startgroup=new"
)

add_group_inline_markup = InlineKeyboardMarkup(inline_keyboard=[[add_group_inline_button]])

async def invite_channel_inline_markup(title, username):
    ch_title = f"{title[:50]}..." if len(title) > 50 else title
    invite_channel_inline_button = InlineKeyboardButton(
        text=f"📢 {ch_title}",
        url=f"https://t.me/{username.lstrip('@')}"
    )
    return InlineKeyboardMarkup(inline_keyboard=[[invite_channel_inline_button], [add_group_inline_button]])