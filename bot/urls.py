from django.urls import path

from bot.views.views import clear_old_messages
from bot.views.webhook.get_webhook import handle_updates
urlpatterns = [
    path("webhook/<str:bot_id>/updates", handle_updates),
    path('clear-old-messages/', clear_old_messages),
]