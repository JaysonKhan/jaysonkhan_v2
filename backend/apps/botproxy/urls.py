from django.urls import path

from botproxy import session_views, views

urlpatterns = [
    # ── Telegram Session Management ─────────────────────────────────────────
    path("telegram/session/", session_views.telegram_session_page, name="telegram_session"),
    path("telegram/session/status/", session_views.telegram_session_status, name="telegram_session_status"),
    path("telegram/session/send-code/", session_views.telegram_session_send_code, name="telegram_session_send_code"),
    path("telegram/session/verify/", session_views.telegram_session_verify, name="telegram_session_verify"),
    path("telegram/session/2fa/", session_views.telegram_session_2fa, name="telegram_session_2fa"),
    path("telegram/session/disconnect/", session_views.telegram_session_disconnect, name="telegram_session_disconnect"),
    path("telegram/session/config/", session_views.telegram_session_save_config, name="telegram_session_config"),
    # ── Bot management ────────────────────────────────────────────────────────
    path("<str:svc>/dashboard/", views.bot_dashboard, name="bot_dashboard"),
    path("<str:svc>/polls/", views.poll_list, name="bot_poll_list"),
    path("<str:svc>/polls/create/", views.poll_create, name="bot_poll_create"),
    path("<str:svc>/polls/<int:poll_id>/", views.poll_detail, name="bot_poll_detail"),
    path("<str:svc>/polls/<int:poll_id>/close/", views.poll_close, name="bot_poll_close"),
    path("<str:svc>/polls/<int:poll_id>/delete/", views.poll_delete, name="bot_poll_delete"),
    path("<str:svc>/polls/<int:poll_id>/export/csv/", views.export_csv, name="bot_export_csv"),
    path("<str:svc>/polls/<int:poll_id>/export/pdf/", views.export_pdf, name="bot_export_pdf"),
    path("<str:svc>/polls/<int:poll_id>/export/json/", views.export_json_view, name="bot_export_json"),
    path("<str:svc>/polls/<int:poll_id>/chart/<str:chart_type>/", views.poll_chart, name="bot_poll_chart"),
    path("<str:svc>/admins/", views.admin_list, name="bot_admin_list"),
    path("<str:svc>/admins/add/", views.admin_add, name="bot_admin_add"),
    path("<str:svc>/admins/<int:user_id>/remove/", views.admin_remove, name="bot_admin_remove"),
    path("<str:svc>/users/", views.user_stats, name="bot_user_stats"),
    path("<str:svc>/users/chart/growth/", views.user_growth_chart, name="bot_user_growth_chart"),
    path("<str:svc>/users/export/csv/", views.export_users_csv, name="bot_export_users_csv"),
    path("<str:svc>/users/<int:user_id>/photo/", views.user_photo_proxy, name="bot_user_photo"),
    # Universities
    path("<str:svc>/universities/", views.university_list, name="bot_university_list"),
    path("<str:svc>/universities/create/", views.university_create, name="bot_university_create"),
    path("<str:svc>/universities/<int:uni_id>/", views.university_detail, name="bot_university_detail"),
    path("<str:svc>/universities/<int:uni_id>/edit/", views.university_edit, name="bot_university_edit"),
    path("<str:svc>/universities/<int:uni_id>/delete/", views.university_delete, name="bot_university_delete"),
    path("<str:svc>/universities/<int:uni_id>/logo/", views.university_logo_proxy, name="bot_university_logo"),
    path("<str:svc>/universities/<int:uni_id>/faculties/", views.university_faculties_api, name="bot_university_faculties"),
]
