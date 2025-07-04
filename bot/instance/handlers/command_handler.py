from aiogram.types import Message
from aiogram import Bot
from asgiref.sync import sync_to_async
import re

from bot.models import TgUser, Group, GroupAdmin, OldMessage, GroupMember
from bot.instance.handlers.keyboards import add_group_inline_markup
from bot.instance.handlers.group_handlers import delete_message, get_group_admins_from_telegram, get_group_member


async def handle_seni(message: Message, bot: Bot):
    await delete_message(message, bot)
    is_private = False

    same_sender = False
    if message.sender_chat and message.chat:
        same_sender = (
                message.sender_chat.id == message.chat.id and
                message.sender_chat.type == message.chat.type
        )

    if message.chat.type == "private":
        msg = await message.answer(
            text="🚫 *Bu buyruq faqat guruhlarda ishlaydi!*",
            reply_markup=add_group_inline_markup,
            parse_mode="Markdown"
        )
        await OldMessage.add(msg.chat.id, msg.message_id)

        return

    chat_id = message.chat.id
    from_user = message.from_user

    # Agar reply bo'lmasa, xatolikni qaytarish
    if not message.reply_to_message:
        msg = await message.answer("❗ Iltimos, bu komandani foydalanuvchi xabariga *reply* qilib yuboring!",
                             parse_mode="Markdown")
        await OldMessage.add(msg.chat.id, msg.message_id)

        return

    replied_user = message.reply_to_message.from_user
    if replied_user.is_bot:
        msg = await message.answer("🤖 Bu foydalanuvchi bot. Iltimos, haqiqiy foydalanuvchini reply qiling.")
        await OldMessage.add(msg.chat.id, msg.message_id)

        return

    # Replied foydalanuvchini bazadan olish yoki yaratish
    tg_user = await TgUser.get_by_chat_id(replied_user.id)
    if not tg_user:
        tg_user = await TgUser.create_tg_user(
            chat_id=replied_user.id,
            full_name=replied_user.full_name,
            is_private=False
        )

    group = await Group.get_by_chat_id(chat_id)
    if not group:
        group = await Group.create_group(chat_id=chat_id, title=message.chat.title)

    # Adminlik tekshiruvi
    if not group.is_admin:
        admins = await get_group_admins_from_telegram(group, bot)
    else:
        admins = [bot.id]

    if bot.id not in admins:
        msg = await message.answer(
            "🚫 Bot guruhda admin emas!\n\n"
            "Botga quyidagi ruxsatlarni bering:\n"
            "✅ Xabarlarni o‘chirish\n"
            "✅ Foydalanuvchilarni cheklash (ban qilish)\n"
            "✅ Xabarlarni pin qilish\n"
            "✅ Xabar yuborish va o‘zgartirish",
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        await OldMessage.add(msg.chat.id, msg.message_id)
        return

    # Faqat adminlar ishlatishi mumkin bo'lgan buyruq
    is_admin = await GroupAdmin.check_admin(group.chat_id, from_user.id)
    if not is_admin and not same_sender:
        msg = await message.answer(
            "❗ Ushbu komandani faqat *adminlar* ishlatishi mumkin!",
            parse_mode="Markdown"
        )
        await OldMessage.add(msg.chat.id, msg.message_id)
        return

    # Foydalanuvchining guruhdagi ma'lumotlarini olish
    group_member = await get_group_member(chat_id=group.chat_id, tg_user_id=tg_user.chat_id)

    # Javob xabari
    msg = await message.answer(
        text=(
            f"🎉 <a href='tg://user?id={tg_user.chat_id}'>{tg_user.full_name}</a> tomonidan "
            f"hozirgacha <b>{group_member.invite_count}</b> ta do‘st guruhga taklif qilingan! 🎯"
        ),
        parse_mode='HTML'
    )
    await OldMessage.add(msg.chat.id, msg.message_id)


async def handle_top_invites(message: Message, bot: Bot):
    try:
        await delete_message(message, bot)

        same_sender = False
        if message.sender_chat and message.chat:
            same_sender = (
                    message.sender_chat.id == message.chat.id and
                    message.sender_chat.type == message.chat.type
            )

        if message.chat.type == "private":
            msg = await message.answer(
                "🚫 *Bu buyruq faqat guruhlarda ishlaydi!*",
                parse_mode="Markdown",
                reply_markup=add_group_inline_markup
            )
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        chat_id = message.chat.id

        group = await Group.get_by_chat_id(chat_id)
        if not group:
            group = await Group.create_group(chat_id=chat_id, title=message.chat.title)

        is_admin = await GroupAdmin.check_admin(group.chat_id, message.from_user.id)
        if not is_admin and not same_sender:
            msg = await message.answer(
                "❗ Ushbu komandani faqat *adminlar* ishlatishi mumkin!",
                parse_mode="Markdown"
            )
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        # TOP 10 eng ko‘p taklif qilganlar — ORM QuerySet ni sinxron tarzda chaqiramiz
        top_members_qs = GroupMember.objects.filter(group_chat=group).select_related('user_chat').order_by('-invite_count')[:10]
        top_members = await sync_to_async(list)(top_members_qs)

        if not top_members:
            msg = await message.answer("😕 Hozircha hech kim hech kimni taklif qilmagan.")
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        # Natijalarni formatlash
        text = "🏆 <b>TOP 10 Do‘st Taklif Qilganlar:</b>\n\n"
        for i, member in enumerate(top_members, 1):
            user = member.user_chat
            text += f"{i}. <a href='tg://user?id={user.chat_id}'>{user.full_name}</a> — <b>{member.invite_count}</b> ta do‘st\n"

        msg = await message.answer(text, parse_mode="HTML")
        await OldMessage.add(msg.chat.id, msg.message_id)

    except Exception as e:
        print(f"❌ Error in handle_top_invites: {e}")
        await message.answer("❗ Ichki xatolik yuz berdi. Iltimos, keyinroq urinib ko‘ring.")

async def handle_ball_command(message: Message, bot: Bot):
    try:
        await delete_message(message, bot)

        same_sender = False
        if message.sender_chat and message.chat:
            same_sender = (
                    message.sender_chat.id == message.chat.id and
                    message.sender_chat.type == message.chat.type
            )

        if message.chat.type == "private":
            msg = await message.answer(
                "🚫 *Bu buyruq faqat guruhlarda ishlaydi!*",
                parse_mode="Markdown",
                reply_markup=add_group_inline_markup
            )
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        # Faqat reply qilingan foydalanuvchiga ishlaydi
        if not message.reply_to_message:
            msg = await message.answer("❗ Iltimos, bu komandani foydalanuvchi xabariga *reply* qilib yuboring!", parse_mode="Markdown")
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        replied_user = message.reply_to_message.from_user
        if replied_user.is_bot:
            msg = await message.answer("🤖 Bu foydalanuvchi bot. Iltimos, haqiqiy foydalanuvchini reply qiling.")
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        # Komandadan raqamni ajratib olish: /ball 4
        match = re.match(r"/bal(?:@\w+)?\s+(\d+)", message.text.strip())
        if not match:
            msg = await message.answer("❗ To‘g‘ri format: <code>/ball 4</code>", parse_mode="HTML")
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        add_count = int(match.group(1))

        # Bazaviy obyektlarni olish
        tg_user = await TgUser.get_by_chat_id(replied_user.id)
        if not tg_user:
            tg_user = await TgUser.create_tg_user(
                chat_id=replied_user.id,
                full_name=replied_user.full_name,
                is_private=False
            )

        group = await Group.get_by_chat_id(message.chat.id)
        if not group:
            group = await Group.create_group(chat_id=message.chat.id, title=message.chat.title)

        # Adminlikni tekshirish
        is_admin = await GroupAdmin.check_admin(group.chat_id, message.from_user.id)
        if not is_admin and not same_sender:
            msg = await message.answer("❗ Bu komandani faqat *adminlar* ishlatishi mumkin!", parse_mode="Markdown")
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        # Foydalanuvchining guruh a'zoligini olish
        group_member = await get_group_member(chat_id=group.chat_id, tg_user_id=tg_user.chat_id)
        if not group_member:
            group_member = await GroupMember.join_group_member(chat_id=group.chat_id, tg_user_id=tg_user.chat_id)

        # Ball qo‘shish
        group_member.invite_count += add_count
        await sync_to_async(group_member.save)()

        # Javob xabari
        msg = await message.answer(
            f"✅ <a href='tg://user?id={tg_user.chat_id}'>{tg_user.full_name}</a> foydalanuvchiga <b>{add_count}</b> ball qo‘shildi.\n"
            f"📊 Umumiy ball: <b>{group_member.invite_count}</b>",
            parse_mode="HTML"
        )
        await OldMessage.add(msg.chat.id, msg.message_id)
    except Exception as e:
        print(f"Error: {e}")

async def handle_nol_command(message: Message, bot: Bot):
    try:
        await delete_message(message, bot)

        same_sender = False
        if message.sender_chat and message.chat:
            same_sender = (
                    message.sender_chat.id == message.chat.id and
                    message.sender_chat.type == message.chat.type
            )

        if message.chat.type == "private":
            msg = await message.answer(
                "🚫 *Bu buyruq faqat guruhlarda ishlaydi!*",
                parse_mode="Markdown",
                reply_markup=add_group_inline_markup
            )
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        if not message.reply_to_message:
            msg = await message.answer("❗ Iltimos, bu komandani foydalanuvchi xabariga *reply* qilib yuboring!", parse_mode="Markdown")
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        replied_user = message.reply_to_message.from_user
        if replied_user.is_bot:
            msg = await message.answer("🤖 Bu foydalanuvchi bot. Iltimos, haqiqiy foydalanuvchini reply qiling.")
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        # Reply qilingan foydalanuvchini olish yoki yaratish
        tg_user = await TgUser.get_by_chat_id(replied_user.id)
        if not tg_user:
            tg_user = await TgUser.create_tg_user(
                chat_id=replied_user.id,
                full_name=replied_user.full_name,
                is_private=False
            )

        # Guruhni olish yoki yaratish
        group = await Group.get_by_chat_id(message.chat.id)
        if not group:
            group = await Group.create_group(chat_id=message.chat.id, title=message.chat.title)

        # Faqat admin ishlata oladi
        is_admin = await GroupAdmin.check_admin(group.chat_id, message.from_user.id)
        if not is_admin  and not same_sender:
            msg = await message.answer("❗ Bu komandani faqat *adminlar* ishlatishi mumkin!", parse_mode="Markdown")
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        # Guruh a'zoligini olish
        group_member = await get_group_member(chat_id=group.chat_id, tg_user_id=tg_user.chat_id)
        if not group_member:
            group_member = await GroupMember.join_group_member(chat_id=group.chat_id, tg_user_id=tg_user.chat_id)

        # Invite count ni 0 ga tushirish
        group_member.invite_count = 0
        await sync_to_async(group_member.save)()

        msg = await message.answer(
            f"🗑 <a href='tg://user?id={tg_user.chat_id}'>{tg_user.full_name}</a> foydalanuvchining ballari nol qilindi.",
            parse_mode="HTML"
        )
        await OldMessage.add(msg.chat.id, msg.message_id)
    except Exception as e:
        print(f"Error: {e}")

async def handle_del_command(message: Message, bot: Bot):
    try:
        await delete_message(message, bot)

        same_sender = False
        if message.sender_chat and message.chat:
            same_sender = (
                    message.sender_chat.id == message.chat.id and
                    message.sender_chat.type == message.chat.type
            )

        if message.chat.type == "private":
            msg = await message.answer(
                "🚫 *Bu buyruq faqat guruhlarda ishlaydi!*",
                parse_mode="Markdown",
                reply_markup=add_group_inline_markup
            )
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        chat_id = message.chat.id

        # Guruhni olish yoki yaratish
        group = await Group.get_by_chat_id(chat_id)
        if not group:
            group = await Group.create_group(chat_id=chat_id, title=message.chat.title)

        # Faqat admin ishlata oladi
        is_admin = await GroupAdmin.check_admin(group.chat_id, message.from_user.id)
        if not is_admin and not same_sender:
            msg = await message.answer("❗ Bu komandani faqat *adminlar* ishlatishi mumkin!", parse_mode="Markdown")
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        # Guruhga tegishli barcha a'zolarni olish
        all_members = await sync_to_async(list)(
            GroupMember.objects.filter(group_chat=group)
        )

        if not all_members:
            msg = await message.answer("😕 Guruhda hali hech kim ro‘yxatga olinmagan.")
            await OldMessage.add(msg.chat.id, msg.message_id)
            return

        # Barchaning ballarini 0 ga tushurish
        for member in all_members:
            member.invite_count = 0

        # Bulk update orqali saqlash (yagona query)
        await sync_to_async(GroupMember.objects.bulk_update)(all_members, ['invite_count'])

        msg = await message.answer(
            "✅ Guruhdagi barcha foydalanuvchilarning taklif soni (ballari) nol qilindi.",
            parse_mode="HTML"
        )
        await OldMessage.add(msg.chat.id, msg.message_id)

    except Exception as e:
        print(f"❗ Error in /del command: {e}")
