from celery import shared_task
from aiogram import Bot
import asyncio
from config.settings import BOT_TOKEN

@shared_task
def delete_message_later(chat_id, message_id, delay_seconds=25):
    async def delete():
        try:
            bot = Bot(token=BOT_TOKEN)
            await asyncio.sleep(delay_seconds)
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            pass

    asyncio.run(delete())
