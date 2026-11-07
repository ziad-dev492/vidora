from django.urls import path
from . import views

urlpatterns = [
    path("", views.admin_dashboard, name="admin_dashboard"),
    path("reports/<int:pk>/", views.update_report, name="report_update"),
    path("channels/<int:pk>/suspend/", views.suspend_channel, name="channel_suspend"),
    path("users/<int:pk>/active/", views.toggle_user_active, name="user_active_toggle"),
    path("categories/manage/", views.manage_category, name="category_manage"),
]
