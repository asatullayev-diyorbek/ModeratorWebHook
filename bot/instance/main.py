from aiogram import Bot, Dispatcher, types
from aiogram.filters import (
    CommandStart,
    Command,
    ChatMemberUpdatedFilter,
    MEMBER,
    IS_NOT_MEMBER,
    ADMINISTRATOR,
    LEFT,
    KICKED,
    CREATOR,
)

from bot.instance.handlers.command_handler import handle_seni, handle_top_invites, handle_ball_command, \
    handle_nol_command, handle_del_command
from bot.instance.handlers.group_handlers import (
    handle_start,
    handle_help,
    join_member,
    left_member,
    all_message,
    admin_changed, edited_message
)

from bot.instance.handlers.admin_handler import (
    handle_guruh,
    handle_kanal, handle_meni,
)

webhook_dp = Dispatcher()
webhook_dp.message.register(handle_start, CommandStart())  # /start
webhook_dp.message.register(handle_help, Command('help')) # /help
webhook_dp.message.register(handle_guruh, Command('guruh'))
webhook_dp.message.register(handle_kanal, Command('kanal'))
webhook_dp.message.register(handle_meni, Command('meni'))
webhook_dp.message.register(handle_seni, Command('sizni'))
webhook_dp.message.register(handle_top_invites, Command('top'))
webhook_dp.message.register(handle_ball_command, Command('bal'))
webhook_dp.message.register(handle_nol_command, Command('nol'))
webhook_dp.message.register(handle_del_command, Command('del'))

webhook_dp.message.register(all_message)

webhook_dp.edited_message.register(edited_message)

webhook_dp.chat_member.register(join_member, ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> MEMBER))
webhook_dp.chat_member.register(left_member, ChatMemberUpdatedFilter(member_status_changed=MEMBER >> IS_NOT_MEMBER))
webhook_dp.chat_member.register(admin_changed, ChatMemberUpdatedFilter(member_status_changed=MEMBER >> ADMINISTRATOR))
webhook_dp.chat_member.register(admin_changed, ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR >> MEMBER))
webhook_dp.chat_member.register(admin_changed, ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR >> LEFT))
webhook_dp.chat_member.register(admin_changed, ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR >> KICKED))
webhook_dp.chat_member.register(admin_changed, ChatMemberUpdatedFilter(member_status_changed=CREATOR >> ADMINISTRATOR))
webhook_dp.chat_member.register(admin_changed, ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR >> CREATOR))



async def feed_update(token: str, update: dict):

    try:
        webhook_book = Bot(token=token)
        aiogram_update = types.Update(**update)
        await webhook_dp.feed_update(bot=webhook_book, update=aiogram_update)
    finally:
        await webhook_book.session.close()