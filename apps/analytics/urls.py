from django.urls import path
from . import views
urlpatterns = [path("", views.dashboard, name="dashboard"), path("videos/", views.video_manage, name="video_manage")]
