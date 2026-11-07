from django.urls import path
from . import views

urlpatterns = [
    path("videos/<int:pk>/like/", views.like_video, name="like"),
    path("channels/<slug:slug>/subscribe/", views.toggle_subscription, name="subscribe"),
    path("videos/<int:pk>/comment/", views.add_comment, name="comment"),
    path("comments/<int:pk>/edit/", views.edit_comment, name="edit_comment"),
    path("comments/<int:pk>/delete/", views.delete_comment, name="delete_comment"),
    path("report/", views.report_content, name="report"),
]
