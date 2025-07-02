from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from bot.models import OldMessage
from aiogram import Bot
from config import settings  # tokenni settings yoki .env dan oling

@csrf_exempt
async def clear_old_messages(request):
    if request.method != "GET":
        return JsonResponse({'error': 'Only GET method allowed'}, status=405)

    bot = Bot(token=settings.BOT_TOKEN)  # Dinamik, toza obyekt

    deleted_count = 0
    db_deleted = 0
    errors = []

    try:
        old_messages = await OldMessage.get_old()
    except Exception as e:
        return JsonResponse({
            'deleted': 0,
            'error': f"Xatolik: ma'lumotlarni olishda xato: {str(e)}"
        }, status=500)

    for msg in old_messages:
        try:
            await bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)
            deleted_count += 1
        except Exception as bot_error:
            errors.append(f"Telegram xabar o'chirish xatosi: {str(bot_error)}")

        try:
            await msg.remove()
            db_deleted += 1
        except Exception as db_error:
            errors.append(f"Baza o'chirish xatosi: {str(db_error)}")

    return JsonResponse({
        'telegram_deleted': deleted_count,
        'db_deleted': db_deleted,
        'errors': errors,
        'timestamp': now().isoformat()
    })
