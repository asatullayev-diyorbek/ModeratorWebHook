import asyncio
import datetime
import re

from aiogram.types import Message, ChatMemberUpdated, ChatPermissions
from aiogram import Bot

from bot.tasks import delete_message_later

from bot.models import TgUser, Group, GroupMember, GroupAdmin, GroupMemberInvitedHistory, ChannelMember, Word
from bot.instance.handlers.keyboards import add_group_inline_markup, invite_channel_inline_markup




async def get_group_admins_from_telegram(group, bot: Bot):
    try:
        # Telegramdan joriy adminlar ro'yxatini olish
        admins = await bot.get_chat_administrators(chat_id=group.chat_id)

        # Bazadagi mavjud adminlar ro'yxatini olish
        existing_admins = await GroupAdmin.get_group_admins(group_chat=group.chat_id)
        existing_admins_chat_ids = [admin.user_chat.chat_id for admin in existing_admins]

        # Telegramdan kelgan adminlarning chat_id larini olish
        telegram_admins_chat_ids = [admin.user.id for admin in admins]
        group_admins_chat_ids = []

        # Yangi adminlarni qo'shish
        for admin in admins:
            if admin.user.id in existing_admins_chat_ids:
                group_admins_chat_ids.append(admin.user.id)
                continue

            # TgUser ni olish yoki yaratish
            tg_user = await TgUser.get_by_chat_id(admin.user.id)
            if not tg_user:
                tg_user = await TgUser.create_tg_user(
                    chat_id=admin.user.id,
                    full_name=admin.user.full_name,
                    is_private=False
                )

            # Yangi adminni bazaga qo'shish
            await GroupAdmin.join_group_admin(group=group, tg_user=tg_user)
            group_admins_chat_ids.append(tg_user.chat_id)

        # Bazada bor, lekin Telegramda yo'q adminlarni o'chirish
        for existing_admin in existing_admins:
            if existing_admin.user_chat.chat_id not in telegram_admins_chat_ids:
                await GroupAdmin.remove_group_admin(
                    group_chat_id=group.chat_id,
                    tg_user_chat_id=existing_admin.user_chat.chat_id
                )
                print(f"Admin o'chirildi: {existing_admin.user_chat.chat_id}")

        # Botning admin statusini yangilash
        if bot.id in group_admins_chat_ids or bot.id in existing_admins_chat_ids:
            await group.update_group_admin_status(is_admin=True)
        else:
            await group.update_group_admin_status(is_admin=False)
        return group_admins_chat_ids

    except Exception as e:
        print(f"Error while fetching admins: {e}")
        return []


async def get_group_member(chat_id, tg_user_id):
    group_member = await GroupMember.get_group_member(
        chat_id=chat_id,
        tg_user_id=tg_user_id
    )
    if not group_member:
        group_member = await GroupMember.join_group_member(chat_id=chat_id, tg_user_id=tg_user_id)
    return group_member


async def all_message(message: Message, bot: Bot):
    if message.left_chat_member or message.new_chat_members:
        await delete_message(message, bot)
        return

    chat_id = message.chat.id
    from_user = message.from_user
    is_private = False

    if message.chat.type in ['private']:
        is_private = True

    tg_user = await TgUser.get_by_chat_id(message.from_user.id)

    if not tg_user:
        tg_user = await TgUser.create_tg_user(
            chat_id=from_user.id,
            full_name=from_user.full_name,
            is_private=is_private
        )
    elif not tg_user.is_private and is_private:
        tg_user = await tg_user.update_is_private(is_private=is_private)

    if not message.chat.type in ['group', 'supergroup']:
        return

    group = await Group.get_by_chat_id(chat_id=chat_id)
    if not group:
        group = await Group.create_group(
            chat_id=chat_id,
            title=message.chat.full_name
        )
        print(f"Guruh qo'shildi! {chat_id};  {message.chat.full_name}")

    group_member = await get_group_member(chat_id=group.chat_id, tg_user_id=tg_user.chat_id)
    if not group.is_admin:
        admins = await get_group_admins_from_telegram(group, message.bot)
    else:
        admins = [group.chat_id]

    if not group.chat_id in admins:
        return

    if await GroupAdmin.check_admin(group.chat_id, tg_user.chat_id):
        return

    # odam qo'shi majburiyatini tekshirish
    if group_member.invite_count < group.required_members:
        msg = await message.answer(
            text=(
                f"🚫 [{message.from_user.first_name}](tg://user?id={message.from_user.id}), "
                "*xabar yuborish uchun ko'proq a'zo taklif qilishingiz kerak!*\n\n"
                f"📊 *Hozirgi holat*: Siz {group_member.invite_count} ta a'zo taklif qildingiz.\n"
                f"🎯 *Talab*: Guruhga {group.required_members} ta a'zo taklif qilish kerak.\n"
                f"🔢 *Yana kerak*: {group.required_members - group_member.invite_count} ta a'zo taklif qiling.\n"
                "📌 Iltimos, yetishmayotgan a'zolarni taklif qiling va keyin xabar yozing!\n\n"
                "📌 *Eslatma*: Siz 1 daqiqaga xabar yuborishdan cheklandingiz."
            ),
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup,
        )

        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        delete_message_later.delay(chat_id=msg.chat.id, message_id=msg.message_id)
        return

    # Kanalga a'zo bo'lishini tekshirish
    if group.required_channel and not await ChannelMember.check_member(group.required_channel, tg_user.chat_id):
        msg = await message.answer(
            text=(
                f"🚫 [{message.from_user.first_name}](tg://user?id={message.from_user.id}), "
                "*xabar yuborish uchun quyidagi kanalga qo'shilishingiz kerak!*\n\n"
                "📌 *Eslatma*: Agar kanalga qo'shilgan bo'lsangiz, lekin xabar yozolmayotgan bo'lsangiz, "
                "kanaldan chiqib, qayta qo'shiling va keyin xabar yuborib ko'ring!"
            ),
            parse_mode="Markdown",
            reply_markup=await invite_channel_inline_markup(group.required_channel_title, group.required_channel_username)
        )

        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        delete_message_later.delay(chat_id=msg.chat.id, message_id=msg.message_id)
        return

    if message.from_user.first_name == 'channel':
        msg = await message.answer(
            text=(
                f"🚫 Kanal nomidan xabar yuborish mumkin emas!\n\n"
                "📌 Iltimos, shaxsiy hisobingizdan xabar yozing."
            ),
            parse_mode="Markdown"
        )

        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        delete_message_later.delay(chat_id=msg.chat.id, message_id=msg.message_id)
        return

    if message.forward_date or message.story or message.link_preview_options:
        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        return

    if await is_blocked_message(message.text):
        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        return

    if has_link(message.html_text):
        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        return


async def edited_message(message: Message, bot: Bot):
    chat_id = message.chat.id
    from_user = message.from_user
    is_private = False

    if message.chat.type in ['private']:
        is_private = True

    tg_user = await TgUser.get_by_chat_id(message.from_user.id)

    if not tg_user:
        tg_user = await TgUser.create_tg_user(
            chat_id=from_user.id,
            full_name=from_user.full_name,
            is_private=is_private
        )
    elif not tg_user.is_private and is_private:
        tg_user = await tg_user.update_is_private(is_private=is_private)

    if not message.chat.type in ['group', 'supergroup']:
        return

    group = await Group.get_by_chat_id(chat_id=chat_id)
    if not group:
        group = await Group.create_group(
            chat_id=chat_id,
            title=message.chat.full_name
        )
        print(f"Guruh qo'shildi! {chat_id};  {message.chat.full_name}")

    group_member = await get_group_member(chat_id=group.chat_id, tg_user_id=tg_user.chat_id)
    if not group.is_admin:
        admins = await get_group_admins_from_telegram(group, message.bot)
    else:
        admins = [group.chat_id]

    if not group.chat_id in admins:
        return

    if await GroupAdmin.check_admin(group.chat_id, tg_user.chat_id):
        return

    # odam qo'shi majburiyatini tekshirish
    if group_member.invite_count < group.required_members:
        msg = await message.answer(
            text=(
                f"🚫 [{message.from_user.first_name}](tg://user?id={message.from_user.id}), "
                "*xabar yuborish uchun ko'proq a'zo taklif qilishingiz kerak!*\n\n"
                f"📊 *Hozirgi holat*: Siz {group_member.invite_count} ta a'zo taklif qildingiz.\n"
                f"🎯 *Talab*: Guruhga {group.required_members} ta a'zo taklif qilish kerak.\n"
                f"🔢 *Yana kerak*: {group.required_members - group_member.invite_count} ta a'zo taklif qiling.\n"
                "📌 Iltimos, yetishmayotgan a'zolarni taklif qiling va keyin xabar yozing!\n\n"
                "📌 *Eslatma*: Siz 1 daqiqaga xabar yuborishdan cheklandingiz."
            ),
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup,
        )

        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        delete_message_later.delay(chat_id=msg.chat.id, message_id=msg.message_id)
        return

    # Kanalga a'zo bo'lishini tekshirish
    if group.required_channel and not await ChannelMember.check_member(group.required_channel, tg_user.chat_id):
        msg = await message.answer(
            text=(
                f"🚫 [{message.from_user.first_name}](tg://user?id={message.from_user.id}), "
                "*xabar yuborish uchun quyidagi kanalga qo'shilishingiz kerak!*\n\n"
                "📌 *Eslatma*: Agar kanalga qo'shilgan bo'lsangiz, lekin xabar yozolmayotgan bo'lsangiz, "
                "kanaldan chiqib, qayta qo'shiling va keyin xabar yuborib ko'ring!"
            ),
            parse_mode="Markdown",
            reply_markup=await invite_channel_inline_markup(group.required_channel_title, group.required_channel_username)
        )

        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        delete_message_later.delay(chat_id=msg.chat.id, message_id=msg.message_id)
        return

    if message.from_user.first_name == 'channel':
        msg = await message.answer(
            text=(
                f"🚫 Kanal nomidan xabar yuborish mumkin emas!\n\n"
                "📌 Iltimos, shaxsiy hisobingizdan xabar yozing."
            ),
            parse_mode="Markdown"
        )

        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        delete_message_later.delay(chat_id=msg.chat.id, message_id=msg.message_id)
        return

    if message.forward_date or message.story or message.link_preview_options:
        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        return

    if await is_blocked_message(message.text):
        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        return

    if has_link(message.html_text):
        await delete_message(message, bot)
        await restrict_user(group.chat_id, tg_user.chat_id, bot)
        return


async def admin_changed(event: ChatMemberUpdated, bot: Bot):
    print('Status changed')

    old_status = event.old_chat_member.status if event.old_chat_member else None
    new_status = event.new_chat_member.status if event.new_chat_member else None
    chat_id = event.chat.id  # Guruhning chat_id si
    user = event.new_chat_member.user  # Foydalanuvchining user_id si

    if old_status and new_status:
        # Guruh va foydalanuvchi obyektlarini olish yoki yaratish
        group = await Group.get_by_chat_id(chat_id) or await Group.create_group(chat_id, title=None)
        tg_user = await TgUser.get_by_chat_id(user.id) or await TgUser.create_tg_user(
            chat_id=user.id,
            full_name=user.full_name
        )

        if old_status == "member" and new_status == "administrator":
            print(f"{event.from_user.full_name} yangi admin qilib tayinlandi!")
            # Yangi adminni bazaga qo'shish
            await GroupAdmin.join_group_admin(group, tg_user)

        elif old_status == "administrator" and new_status == "member":
            print(f"{event.from_user.full_name} adminlikdan olindi!")
            # Adminlikdan olinayotgan foydalanuvchini bazadan o'chirish
            await GroupAdmin.remove_group_admin(group.chat_id, tg_user.chat_id)

        elif old_status == "administrator" and new_status in ["left", "kicked"]:
            print(f"{event.from_user.full_name} admin bo'lib chiqdi yoki haydaldi!")
            # Agar kerak bo'lsa, bazadan o'chirish
            await GroupAdmin.remove_group_admin(group.chat_id, tg_user.chat_id)

        elif old_status == "creator" and new_status == "administrator":
            print(f"{event.from_user.full_name} yangi admin qilib tayinlandi! (Oldin creator edi)")
            # Creator dan admin ga o'tganida ham bazaga qo'shish
            await GroupAdmin.join_group_admin(group, tg_user)

        elif old_status == "administrator" and new_status == "creator":
            print(f"{event.from_user.full_name} endi guruh yaratuvchisi!")
            # Admin dan creator ga o'tganida bazadan o'chirish kerak bo'lmasligi mumkin, chunki creator alohida rol
            await GroupAdmin.remove_group_admin(group.chat_id, tg_user.chat_id)

        else:
            print(f"{event.from_user.full_name} ning statusi o'zgardi: {old_status} -> {new_status}")

async def left_member(event: ChatMemberUpdated, bot: Bot):
    chat = event.chat
    left_user = event.old_chat_member.user

    if chat.type == 'channel':
        await ChannelMember.remove_member(
            chat.id,
            left_user.id
        )
        print(f"{chat.title} -> {left_user.full_name} left")
        return


async def join_member(event: ChatMemberUpdated, bot: Bot):
    chat = event.chat
    from_user = event.from_user
    invite_user = event.new_chat_member.user

    if chat.type == 'channel':
        await ChannelMember.join_channel(
            chat.id,
            invite_user.id
        )
        print(f"{chat.title} -> {invite_user.full_name} join")
        return

    if from_user.id != invite_user.id:
        # Guruhni olish yoki yaratish
        group = await Group.get_by_chat_id(chat.id) or await Group.create_group(chat_id=chat.id, title=chat.title)
        # Foydalanuvchini olish yoki yaratish
        tg_user = await TgUser.get_by_chat_id(from_user.id) or await TgUser.create_tg_user(
            chat_id=from_user.id,
            full_name=from_user.full_name  # full_name to'g'ri olingan
        )

        # Guruh a'zosini tekshirish
        group_member = await GroupMember.get_group_member(group.chat_id, tg_user.chat_id)
        if not group_member:
            # Agar a'zo bo'lmasa, yangi qo'shish va invite_count ni 1 qilib boshlash
            group_member = await GroupMember.join_group_member(group.chat_id, tg_user.chat_id)

        invited_history = await GroupMemberInvitedHistory.create_invite_history(group_member, invite_user.id)

        if invited_history:
            # Yangi qo'shilgan foydalanuvchi uchun invite_count ni oshirish (birinchi marta qo'shilganida)
            await group_member.update_count()  # Birinchi marta qo'shilganda count ni 1 qilish
            print(f"{event.from_user.full_name} {invite_user.full_name} join group")
        else:
            # Agar allaqachon a'zo bo'lsa, hech narsa qilmaslik
            print(f"{event.from_user.full_name} avval {invite_user.full_name} ni qo'shgan ekan")
            pass


async def handle_start(message: Message, bot: Bot) -> None:
    try:
        await message.delete()
    except:
        pass

    chat_id = message.chat.id
    from_user = message.from_user
    is_private = False

    if message.chat.type in ['private']:
        is_private = True

    tg_user = await TgUser.get_by_chat_id(message.from_user.id)

    if not tg_user:
        tg_user = await TgUser.create_tg_user(
            chat_id=from_user.id,
            full_name=from_user.full_name,
            is_private=is_private
        )
    elif not tg_user.is_private and is_private:
        tg_user = await tg_user.update_is_private(is_private=is_private)

    if message.chat.type in ['group', 'supergroup']:
        group = await Group.get_by_chat_id(chat_id=chat_id)
        if not group:
            group = await Group.create_group(
                chat_id=chat_id,
                title=message.chat.full_name
            )
            print(f"Guruh qo'shildi! {chat_id};  {message.chat.full_name}")

        group_member = await get_group_member(chat_id=group.chat_id, tg_user_id=tg_user.chat_id)
        if not group.is_admin:
            admins = await get_group_admins_from_telegram(group, message.bot)

    text = """
👋 Assalomu alaykum !

🤖Men guruhingizni tartibga solishda yordam beruvchi botman.

1) 📣 KANALGA ODAM YIGʻISH - Man guruhingizdagi azolarni kanalga azo bolmaguncha yozdirmayman ❗️

2) 👥 GURUHGA ODAM YIGʻISH- Man guruhingizga azolarni odam qoshmaguncha yozdirmayman👮‍♂️

2) 🗑 KIRDI-CHIQTI TOZALASH - Man guruhdagi foydalanuvchi guruhga qoʻshildi yokiguruhni tark etdi degan xabarlarini oʻchiraman.

3) 📊 XISOBLAB SANAYDI - Man Guruhga kim qancha odam qo'shganligini aytib beraman

4) ⛔️REKLAMA 🚯SPAM 🚫SSILKA -arab va reklamalarni, ssilkalani guruhlarda ochirib beraman👨🏻‍✈️

5) 🔞 SOKINMANG- Sokinish, Xaqoratli, Axloqsiz sozlarni ochirishda yordam beradi

6) ❌ KANAL NOMIDAN YOZISHNI TAQIQLIMAN 


👨🏻‍💻 Bot guruhda ADMIN bo`lsa ishlaydi !

👉 /help - 🔖 TEKSLI QOLLANMA

🎥 @Video_qollanma_kanali
"""

    msg = await message.bot.send_message(
        chat_id=message.chat.id,  
        text=text,
        parse_mode='HTML',
        reply_markup=add_group_inline_markup
    )

    if not is_private:
        try:
            delete_message_later.delay(chat_id=msg.chat.id, message_id=msg.message_id)
        except Exception as e:
            print("Yubrishda muammo")
            print(e)


async def handle_help(message: Message, bot: Bot) -> None:
    try:
        await message.delete()
    except:
        pass

    chat_id = message.chat.id
    from_user = message.from_user
    is_private = False

    if message.chat.type in ['private']:
        is_private = True

    tg_user = await TgUser.get_by_chat_id(message.from_user.id)

    if not tg_user:
        tg_user = await TgUser.create_tg_user(
            chat_id=from_user.id,
            full_name=from_user.full_name,
            is_private=is_private
        )
    elif not tg_user.is_private and is_private:
        tg_user = await tg_user.update_is_private(is_private=is_private)

    if message.chat.type in ['group', 'supergroup']:
        group = await Group.get_by_chat_id(chat_id=chat_id)
        if not group:
            group = await Group.create_group(
                chat_id=chat_id,
                title=message.chat.full_name
            )
            print(f"Guruh qo'shildi! {chat_id};  {message.chat.full_name}")

        group_member = await get_group_member(chat_id=group.chat_id, tg_user_id=tg_user.chat_id)

        # Agar bazadagi ma'lumotda bot guruhda admin bo'lmasa qayta tekshirib tekshirib ko'ramiz
        if not group.is_admin:
            admins = await get_group_admins_from_telegram(group, message.bot)

    text = """
🤖 Bot buyruqlari:

📣 KANALGA ODAM YIGʻISH
/kanal @LiderAvtoUz  - Kanalga odam yigʻishni ulash, guruhga junatasiz !

❗️eslatma: - @LiderAvtoUz ga kanalingiz useri
/kanal off - o'chirish
_________________________

👥GURUHGA ISTAGANCHA ODAM YIGISH

/guruh 5 - majburiy odam qo'shishni yoqish  !

❗️Eslatma: 5 soni o'rniga istagan raqamizni yozib jonatishiz mumkin!

/guruh 0 - majburiy odam qo'shishni o'chirib qoyish uchun!
___________________________

📊GURUHGA KIM QANCHA ODAM QO'SHGANLIGINI ANIQLASH !
_
/bal - 🎁Bal berib odam qo'shganlik sonini ko'paytirish!
/meni - 📊Siz qo'shgan odamlar soni!
/sizni - 📈Aynan 1 odamning, guruhga qo'shgan odamlar soni!
/top  - 🏆Eng ko'p odam qo'shgan 10 talik!
/nol - 🪓Aynan 1 odam malumotini 0 ga tushirish!
/del - 🗑Barcha odam qo'shganlar malumotini tozalash!

👨🏻‍✈️ Bot guruhda ADMIN bo'lsa ishlaydi !

🎥 @Video_qollanma_kanali
"""

    msg = await message.bot.send_message(
        chat_id=message.chat.id,
        text=text,
        parse_mode='HTML',
        reply_markup=add_group_inline_markup
    )

    if not is_private:
        try:
            delete_message_later.delay(chat_id=msg.chat.id, message_id=msg.message_id)
        except Exception as e:
            print("O'chirishda muammo")
            print(e)


# Kerakli funksiyalar

async def delete_message(message: Message, bot: Bot):
    """
    Xabarni o'chirish funksiyasi. Agar xatolik chiqsa, Telegram API orqali botning admin
    statusini tekshiradi va agar admin bo'lmasa, botni adminlar ro'yxatidan o'chiradi
    va guruhning is_admin fieldini False qiladi.
    """
    chat_id = message.chat.id
    message_id = message.message_id

    try:
        # Xabarni o'chirishga urinish
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        print(f"Xabar o'chirildi: chat_id={chat_id}, message_id={message_id}")

    except Exception as e:
        print(f"Xatolik: Bot xabarni o'chira olmadi. Xato: {str(e)}")
        if "message to delete not found" in e:
            print(f"⚠️ Xabar topilmadi: chat_id={chat_id}, message_id={message_id}")
            return

        # Telegram API orqali botning admin statusini tekshirish
        try:
            admins = await bot.get_chat_administrators(chat_id=chat_id)
            bot_is_admin = any(admin.user.id == bot.id for admin in admins)
        except Exception as admin_error:
            print(f"Adminlarni olishda xatolik: {str(admin_error)}")
            bot_is_admin = False  # Agar adminlarni olishda xatolik bo'lsa, bot admin emas deb hisoblaymiz

        # Agar bot admin bo'lmasa
        if not bot_is_admin:
            # Guruhni olish
            group = await Group.get_by_chat_id(chat_id)
            if group:
                # Botni GroupAdmin ro'yxatidan o'chirish
                bot_user = await TgUser.get_by_chat_id(bot.id)
                if bot_user:
                    await GroupAdmin.remove_group_admin(
                        group_chat_id=group.chat_id,
                        tg_user_chat_id=bot_user.chat_id
                    )
                    print(f"Bot {bot_user.chat_id} adminlar ro'yxatidan o'chirildi.")

                # Guruhning is_admin fieldini False qilish
                await group.update_group_admin_status(is_admin=False)
                print(f"Guruh {group.chat_id} uchun is_admin=False qilindi.")
        else:
            print(f"Bot hali ham admin: chat_id={chat_id}")


async def restrict_user(group_chat_id, user_chat_id, bot):
    # Foydalanuvchini 1 daqiqaga cheklash
    try:
        until_date = datetime.datetime.now() + datetime.timedelta(minutes=1)
        await bot.restrict_chat_member(
            chat_id=group_chat_id,
            user_id=user_chat_id,
            permissions=ChatPermissions(
                can_send_messages=False,  # Xabar yuborish taqiqlanadi
                can_send_media_messages=False,  # Media yuborish taqiqlanadi
                can_send_polls=False,  # So'rovnomalar taqiqlanadi
                can_send_other_messages=False,  # Stikerlar, GIFlar taqiqlanadi
                can_add_web_page_previews=False,  # Veb sahifa havolalari taqiqlanadi
                can_invite_users=True
            ),
            until_date=until_date
        )
    except Exception as e:
        print(f"Foydalanuvchini cheklashda xato: {e}")

# Linklarni tekshirish
def has_link(text: str) -> bool:
    link_pattern = r"""
        (?:
            (?:https?://|www\.)             
            |                                
            [a-zA-Z0-9-]+\.[a-zA-Z]{2,}       
            |                                 
            @[\w\d_]+                          
        )
        [^\s]*                                
    """
    return bool(re.search(link_pattern, text, re.VERBOSE | re.IGNORECASE))


async def contains_blocked_word(text: str, words_subset: set) -> bool:
    words = text.lower().split()
    return any(word in words_subset for word in words)


async def is_blocked_message(text: str) -> bool:
    # Taqiqlangan so'zlarni olish
    blocked_words = await Word.get_words()
    if not blocked_words:
        return False

    # So'zlarni set ga aylantirish
    blocked_words_set = set(word.lower() for word in blocked_words)

    # Kichik ro'yxatlar uchun to'g'ridan-to'g'ri tekshirish
    if len(blocked_words_set) <= 100:
        return await contains_blocked_word(text, blocked_words_set)

    # Katta ro'yxatlar uchun parallel tekshirish
    num_tasks = max(len(blocked_words_set) // 50, 1)
    word_chunks = [
        list(blocked_words_set)[i:i + (len(blocked_words_set) // num_tasks)]
        for i in range(0, len(blocked_words_set), len(blocked_words_set) // num_tasks)
    ]

    tasks = [contains_blocked_word(text, set(chunk)) for chunk in word_chunks]
    results = await asyncio.gather(*tasks)
    return any(results)