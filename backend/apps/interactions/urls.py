from django.urls import path
from .views import TelegramAuthView, TelegramLogoutView, AddCommentView, ToggleLikeView

app_name = 'interactions'

urlpatterns = [
    # Telegram Login Widget callback + logout
    path('auth/telegram/',        TelegramAuthView.as_view(),  name='telegram_auth'),
    path('auth/telegram/logout/', TelegramLogoutView.as_view(), name='telegram_logout'),

    # Comment submit
    path(
        'interactions/comment/<str:app_label>/<str:model_name>/<int:object_id>/',
        AddCommentView.as_view(),
        name='add_comment',
    ),
    # Like toggle (AJAX)
    path(
        'interactions/like/<str:app_label>/<str:model_name>/<int:object_id>/',
        ToggleLikeView.as_view(),
        name='toggle_like',
    ),
]
