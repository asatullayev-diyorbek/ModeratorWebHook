from aiogram.types import Message
from aiogram import Bot

from bot.models import TgUser, Group, GroupAdmin
from bot.instance.handlers.keyboards import add_group_inline_markup
from bot.instance.handlers.group_handlers import delete_message, get_group_admins_from_telegram, get_group_member


async def handle_meni(message: Message, bot: Bot):
    await delete_message(message, bot)
    is_private = False

    if message.chat.type == "private":
        await message.answer(
            text=(
                "🚫 *Bu buyruq faqat guruhlarda ishlaydi!*\n\n"
                "👥 Iltimos, bu buyrugʻdan guruhda foydalaning: `/meni`\n"
                "📌 Guruhda botni administrator qilib, nechta a'zo qo'shganingizni bilib olishingiz mumkin bo'ladi\n"
                "ℹ️ Misol uchun: `/meni`"
            ),
            reply_markup=add_group_inline_markup,
            parse_mode="Markdown"
        )
        is_private = True


    chat_id = message.chat.id
    from_user = message.from_user

    tg_user = await TgUser.get_by_chat_id(message.from_user.id)

    if not tg_user:
        tg_user = await TgUser.create_tg_user(
            chat_id=from_user.id,
            full_name=from_user.full_name,
            is_private=is_private
        )
    elif not tg_user.is_private and is_private:
        tg_user = await tg_user.update_is_private(is_private=is_private)

    if message.chat.type == 'channel' or is_private:
        return

    group = await Group.get_by_chat_id(chat_id)
    if not group:
        group = await Group.create_group(chat_id=chat_id, title=message.chat.title)

    if not group.is_admin:
        admins = await get_group_admins_from_telegram(group, message.bot)
    else:
        admins = [bot.id]

    if not bot.id in admins:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="🚫 Bot guruhda admin emas!\n\n"
                 "Botga quyidagi ruxsatlarni bering:\n"
                 "✅ Xabarlarni o‘chirish\n"
                 "✅ Foydalanuvchilarni cheklash (ban qilish)\n"
                 "✅ Xabarlarni pin qilish\n"
                 "✅ Xabar yuborish va o‘zgartirish\n\n",
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        
        return

    group_member = await get_group_member(chat_id=group.chat_id, tg_user_id=tg_user.chat_id)

    await message.answer(
        text=(
            f"🎉 <a href='tg://user?id={tg_user.chat_id}'>{tg_user.full_name}</a>, ajoyib natija! 👏\n\n"
            f"🔗 Siz hozirgacha {group_member.invite_count} ta do‘stni guruhga taklif qildingiz! 🎯\n"
        ),
        parse_mode='HTML'
    )
    


async def handle_guruh(message: Message, bot: Bot):
    # Xabarni o'chirishga
    await delete_message(message, bot)

    # Agar xabar shaxsiy suhbatdan kelsa
    if message.chat.type == "private":
        await message.answer(
            text="🚫 *Bu buyruq faqat guruhlarda ishlaydi!*\n\n"
                 "👥 Iltimos, guruhda `/guruh` buyrug'idan foydalaning.\n"
                 "📌 Guruhda botni admin qilib, majburiy a'zolar sonini sozlashingiz mumkin!\n"
                 "ℹ️ Masalan: `/guruh 5` yoki `/guruh 0`",
            reply_markup=add_group_inline_markup,
            parse_mode="Markdown"
        )
        return

    if message.chat.type == 'channel':
        return

    chat_id = message.chat.id
    from_user = message.from_user

    group = await Group.get_by_chat_id(chat_id)
    if not group:
        group = await Group.create_group(chat_id=chat_id, title=message.chat.title)

    if not group.is_admin:
        admins = await get_group_admins_from_telegram(group, message.bot)
    else:
        admins = [bot.id]

    if not bot.id in admins:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="🚫 Bot guruhda admin emas!\n\n"
                 "Botga quyidagi ruxsatlarni bering:\n"
                 "✅ Xabarlarni o‘chirish\n"
                 "✅ Foydalanuvchilarni cheklash (ban qilish)\n"
                 "✅ Xabarlarni pin qilish\n"
                 "✅ Xabar yuborish va o‘zgartirish\n\n",
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        
        return

    if not await GroupAdmin.check_admin(chat_id, from_user.id):
        print(f"Chat: {chat_id}   User: {from_user.id}")
        await message.answer(
            text=(
                f"🚫 [{message.from_user.first_name}](tg://user?id={message.from_user.id}), "
                "*siz guruhda admin emassiz!*\n\n"
                "🔐 Bu amalni bajarish uchun guruhda admin huquqlariga ega bo‘lishingiz kerak.\n"
                "📌 Iltimos, guruh adminidan sizga kerakli huquqlarni berishni so‘rang!"
            ),
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        
        return

    # Buyruq argumentlarini olish
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            text="ℹ️ *Majburiy a'zolar sonini kiriting!*\n\n"
                 f"📊 *Hozirgi sozlama*: {str(group.required_members) + ' ta' if group.required_members != 0 else 'Yoqilmagan'}\n\n"
                 "📋 *Qanday ishlatiladi?*\n"
                 "👉 `/guruh 0` — Majburiy qo'shishni o'chirish.\n"
                 "👉 `/guruh <raqam>` — Majburiy a'zolar sonini belgilash.\n\n"
                 "📌 *Misollar*:\n"
                 "✅ `/guruh 5` — 5 ta a'zo qo'shish talab qilinadi.\n"
                 "✅ `/guruh 0` — Talab o'chiriladi.\n\n"
                 "🔢 *Eslatma*: Raqam 0 yoki undan katta bo'lishi kerak!",
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )

        return

    try:
        required_count = int(args[1])  # Raqamni olish
        if required_count < 0:
            await message.answer(
                text="❌ *Raqam 0 yoki undan katta bo'lishi kerak!*\n\n"
                     "🔢 Majburiy a'zolar soni sifatida faqat 0 yoki musbat raqam kiritishingiz mumkin.\n"
                     "📌 Masalan: `/guruh 5` yoki `/guruh 0`",
                parse_mode="Markdown",
                reply_parameters=add_group_inline_markup
            )
            
            return

        if required_count == 0:
            await group.update_required_member_count(required_count=required_count)
            await message.answer(
                text="✅ *Majburiy odam qo'shish o'chirildi!*\n\n"
                     "📴 Endi guruhda majburiy a'zo qo'shish talabi yo'q.\n"
                     "🔄 Agar qayta yoqmoqchi bo'lsangiz, masalan: `/guruh 5`",
                parse_mode="Markdown",
                reply_markup=add_group_inline_markup
            )
            
            return
        else:
            await group.update_required_member_count(required_count=required_count)
            await message.answer(
                text=f"✅ *Majburiy odam qo'shish soni {required_count} ga o'rnatildi!*\n\n"
                     f"👥 Endi guruhga {required_count} ta majburiy a'zo qo'shish kerak.\n"
                     "🔄 O'zgartirish uchun, masalan: `/guruh 0` yoki `/guruh 5`",
                parse_mode="Markdown",
                reply_markup=add_group_inline_markup
            )
            
            return

    except ValueError:
        await message.answer(
            text="❌ *Iltimos, to'g'ri raqam kiriting!*\n\n"
                 "🔢 Faqat raqam kiritishingiz mumkin (0 yoki undan katta).\n"
                 "📌 Masalan: `/guruh 5` yoki `/guruh 0`",
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        
        return

    except:
        await message.answer(
            text="❌ *Nimadir xato ketdi!*\n\n"
                 "🔄 Iltimos qayta urinib ko‘ring.",
            parse_mode="Markdown",
            reply_parameters=add_group_inline_markup
        )
        


async def handle_kanal(message: Message, bot: Bot):
    await delete_message(message, bot)

    if message.chat.type == "private":
        await message.answer(
            text=(
                "🚫 *Bu buyruq faqat guruhlarda ishlaydi!*\n\n"
                "👥 Iltimos, bu buyrugʻdan guruhda foydalaning: `/kanal`\n"
                "📌 Guruhda botni administrator qilib, majburiy kanalga aʼzo bo‘lishni sozlashingiz mumkin.\n"
                "ℹ️ Misol uchun: `/kanal @LiderAvtoUz`"
            ),
            reply_markup=add_group_inline_markup,
            parse_mode="Markdown"
        )
        return

    if message.chat.type == 'channel':
        return

    chat_id = message.chat.id
    from_user = message.from_user

    group = await Group.get_by_chat_id(chat_id)
    if not group:
        group = await Group.create_group(chat_id=chat_id, title=message.chat.title)

    if not group.is_admin:
        admins = await get_group_admins_from_telegram(group, message.bot)
    else:
        admins = [bot.id]

    if not bot.id in admins:
        await message.bot.send_message(
            chat_id=message.chat.id,
            text="🚫 Bot guruhda admin emas!\n\n"
                 "Botga quyidagi ruxsatlarni bering:\n"
                 "✅ Xabarlarni o‘chirish\n"
                 "✅ Foydalanuvchilarni cheklash (ban qilish)\n"
                 "✅ Xabarlarni pin qilish\n"
                 "✅ Xabar yuborish va o‘zgartirish\n\n",
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        
        return

    if not await GroupAdmin.check_admin(chat_id, from_user.id):
        await message.answer(
            text=(
                f"🚫 [{message.from_user.first_name}](tg://user?id={message.from_user.id}), "
                "*siz guruhda admin emassiz!*\n\n"
                "🔐 Bu amalni bajarish uchun guruhda admin huquqlariga ega bo‘lishingiz kerak.\n"
                "📌 Iltimos, guruh adminidan sizga kerakli huquqlarni berishni so‘rang!"
            ),
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            text="ℹ️ *Majburiy kanalga a'zo bo'lish sozlamasini kiriting!*\n\n"
                 f"📊 *Hozirgi sozlama*: {('Yoqilmagan' if not group.required_channel else f'[{group.required_channel_title}](https://t.me/c/{str(group.required_channel)[4:]})')}\n\n"
                 "📋 *Qanday ishlatiladi?*\n"
                 "👉 `/kanal @KanalUserName` — Guruhga majburiy aʼzo boʻlish uchun kanal ulaydi.\n"
                 "👉 `/kanal off` — Majburiy kanalga a'zo bo'lishni oʻchiradi.\n\n"
                 "📌 *Misollar*:\n"
                 "✅ `/kanal @LiderAvtoUz` — @LiderAvtoUz kanaliga aʼzo boʻlish talab qilinadi.\n"
                 "✅ `/kanal off` — Majburiy kanaliga a'zo bo'lish talabi oʻchiriladi.\n\n"
                 "🔢 *Eslatma*: Toʻgʻri kanal usernamesini kiriting (@ bilan) yoki off ni tanlang!",
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        
        return

    kanal_username = args[1]

    if kanal_username.lower() == "off":
        if group.required_channel:
            await group.update_required_channel(None, None)
            await message.answer(
                text="✅ *Majburiy kanalga aʼzo bo‘lish talabi o‘chirildi!*\n\n"
                     "📴 Endi guruhga yozish uchun hech qanday kanalga aʼzo bo‘lish shart emas.",
                parse_mode="Markdown",
                reply_markup=add_group_inline_markup
            )
        else:
            await message.answer(
                text="ℹ️ *Majburiy kanalga aʼzo bo‘lish talabi yoqilmagan!*\n\n"
                     "Yoqish uchun: `/kanal @LiderAvtoUz`",
                parse_mode="Markdown",
                reply_markup=add_group_inline_markup
            )

        
        return

    if not kanal_username.startswith('@'):
        await message.answer(
            text="❌ *Iltimos, kanal usernamesini to‘g‘ri kiriting!*\n\n"
                 "Masalan: `/kanal @LiderAvtoUz`",
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        
        return

    try:
        kanal_info = await bot.get_chat(kanal_username)
        if kanal_info.type != 'channel':
            await message.answer(
                text="❌ *Bu username kanalga tegishli emas!*\n\n"
                     "Faqat kanal usernamesini kiriting.",
                parse_mode="Markdown",
                reply_markup=add_group_inline_markup
            )
            
            return

        try:
            bot_member = await bot.get_chat_member(chat_id=kanal_info.id, user_id=bot.id)
        except:
            await message.answer(
                "❌ *Xatolik!*\n\n"
                "Bot ushbu kanalda mavjud emas yoki kanal topilmadi.\n\n"
                "ℹ️ Iltimos, kanal username'sini to‘g‘ri kiriting va botni kanalga qo‘shganingizga ishonch hosil qiling.",
                parse_mode="Markdown"
            )
            
            return

        if bot_member.status not in ("administrator", "creator"):
            await message.answer(
                "❌ Bot ushbu kanalda *admin* emas.\n\n"
                "ℹ️ Iltimos, botni kanalga admin qilib qo‘shing va qayta urinib ko‘ring.",
                parse_mode="Markdown"
            )
            
            return

        await group.update_required_channel(kanal_info.id, kanal_info.title, kanal_info.username)

        await message.answer(
            text=f"✅ *Kanal muvaffaqiyatli ulandi!*\n\n"
                 f"📢 Kanal: [{kanal_info.title}](https://t.me/{kanal_info.username})\n"
                 "🔒 Endi guruhga yozish uchun ushbu kanalda aʼzo boʻlish shart.",
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        
        return

    except:
        await message.answer(
            text="❌ *Kanal topilmadi yoki xatolik yuz berdi!*\n\n"
                 "📋 Iltimos, to‘g‘ri kanal usernamesini kiriting va botni kanalga admin qiling (kamida 'xabar o'qish' huquqi bo‘lsin).",
            parse_mode="Markdown",
            reply_markup=add_group_inline_markup
        )
        
        return