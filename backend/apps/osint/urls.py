from django.urls import path

from osint import views

urlpatterns = [
    path("search/", views.osint_search, name="osint_search"),
    path("profile/<int:user_id>/", views.osint_profile, name="osint_profile"),
    path("profile/<int:user_id>/branch/<str:branch>/", views.osint_fetch_branch, name="osint_fetch_branch"),
    path("text-search/", views.osint_text_search, name="osint_text_search"),
    path("balance/", views.osint_balance, name="osint_balance"),
    path("photo/<str:entity_id>/", views.osint_photo_proxy, name="osint_photo"),
    # Kanal/Guruh OSINT (Telethon MTProto)
    path("entity/<str:entity_id>/", views.osint_entity_profile, name="osint_entity_profile"),
    path("entity/<str:entity_id>/messages/", views.osint_channel_messages, name="osint_channel_messages"),
    path("entity/<str:entity_id>/search/", views.osint_channel_search, name="osint_channel_search"),
    path("entity/<str:entity_id>/message/<int:msg_id>/photo/", views.osint_message_photo, name="osint_message_photo"),
]
