from django.contrib import admin
from django.urls import path, include


from django.http import HttpResponse

def goto_admin_panel(request):
    return HttpResponse("""
        <!DOCTYPE html>
        <html lang="uz">
        <head>
            <meta charset="UTF-8">
            <title>Admin Panelga</title>
            <style>
                body {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f5f5f5;
                    font-family: Arial, sans-serif;
                }
                a.button {
                    padding: 15px 30px;
                    font-size: 18px;
                    text-decoration: none;
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 8px;
                    transition: background-color 0.3s;
                }
                a.button:hover {
                    background-color: #45a049;
                }
            </style>
        </head>
        <body>
            <a href="/admin/" class="button">Admin Panelga</a>
        </body>
        </html>
    """)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('bot/', include('bot.urls')),
    path('', goto_admin_panel)
]


