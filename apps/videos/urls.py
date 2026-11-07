from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_video, name="upload_video"),
    path("<int:pk>/", views.video_detail, name="video_detail"),
    path("<int:pk>/edit/", views.edit_video, name="edit_video"),
    path("<int:pk>/stream/", views.stream_video, name="stream_video"),
    path("<int:pk>/delete/", views.delete_video, name="video_delete"),
    path("<int:pk>/retry/", views.retry_video_processing, name="video_retry"),
]
