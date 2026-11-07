from django.urls import path
from . import views
urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("shorts/", views.shorts, name="shorts"),
    path("subscriptions/", views.subscriptions, name="subscriptions"),
    path("category/<slug:slug>/", views.category, name="category"),
]
