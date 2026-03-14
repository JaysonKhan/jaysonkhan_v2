from django.urls import path

from botproxy import views

urlpatterns = [
    path("dashboard/", views.bot_dashboard, name="bot_dashboard"),
    path("polls/", views.poll_list, name="bot_poll_list"),
    path("polls/create/", views.poll_create, name="bot_poll_create"),
    path("polls/<int:poll_id>/", views.poll_detail, name="bot_poll_detail"),
    path("polls/<int:poll_id>/close/", views.poll_close, name="bot_poll_close"),
    path("polls/<int:poll_id>/export/csv/", views.export_csv, name="bot_export_csv"),
    path("polls/<int:poll_id>/export/pdf/", views.export_pdf, name="bot_export_pdf"),
    path("polls/<int:poll_id>/export/json/", views.export_json_view, name="bot_export_json"),
    path("polls/<int:poll_id>/chart/<str:chart_type>/", views.poll_chart, name="bot_poll_chart"),
    path("admins/", views.admin_list, name="bot_admin_list"),
    path("admins/add/", views.admin_add, name="bot_admin_add"),
    path("admins/<int:user_id>/remove/", views.admin_remove, name="bot_admin_remove"),
    path("users/", views.user_stats, name="bot_user_stats"),
    path("users/chart/growth/", views.user_growth_chart, name="bot_user_growth_chart"),
    path("users/export/csv/", views.export_users_csv, name="bot_export_users_csv"),
    path("users/<int:user_id>/photo/", views.user_photo_proxy, name="bot_user_photo"),
]
