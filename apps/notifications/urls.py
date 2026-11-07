from django.urls import path
from . import views
urlpatterns = [
    path("", views.notification_list, name="notifications"),
    path("<int:pk>/read/", views.mark_read, name="notification_read"),
]
