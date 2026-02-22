from django.urls import path
from .views import TelegramAuthView, TelegramLogoutView, AddCommentView, ToggleLikeView, ToggleCommentReactionView

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
    # Reaction toggle (AJAX)
    path(
        'interactions/comment/<int:comment_id>/react/',
        ToggleCommentReactionView.as_view(),
        name='toggle_comment_reaction',
    ),
    # Like toggle (AJAX)
    path(
        'interactions/like/<str:app_label>/<str:model_name>/<int:object_id>/',
        ToggleLikeView.as_view(),
        name='toggle_like',
    ),
]
