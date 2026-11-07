from django.urls import path
from . import views

urlpatterns = [
    path("", views.playlist_list, name="playlist_list"),
    path("<int:pk>/", views.playlist_detail, name="playlist_detail"),
    path("<int:pk>/add/", views.add_to_playlist, name="playlist_add"),
    path("<int:pk>/manage/", views.manage_playlist, name="playlist_manage"),
    path("watch-later/", views.watch_later_list, name="watch_later"),
    path("watch-later/<int:pk>/toggle/", views.toggle_watch_later, name="watch_later_toggle"),
    path("history/", views.watch_history, name="history"),
    path("history/clear/", views.clear_history, name="history_clear"),
    path("liked/", views.liked_videos, name="liked_videos"),
]
