from django.urls import path
from .views import channel_detail

urlpatterns = [path("<slug:slug>/", channel_detail, name="channel_detail")]
