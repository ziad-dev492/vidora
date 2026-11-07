from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from apps.videos.api import VideoViewSet
from apps.channels.api import ChannelViewSet
from config.views import hls_asset, media_asset, not_found, route_manifest, server_error, video_thumbnail

router = DefaultRouter()
router.register("videos", VideoViewSet, basename="api-video")
router.register("channels", ChannelViewSet, basename="api-channel")

urlpatterns = [
    path("manus-routes.json", route_manifest, name="route_manifest"),
    path("media/<path:path>", media_asset, name="media_asset"),
    path("videos/<int:pk>/thumbnail/", video_thumbnail, name="video_thumbnail"),
    path("videos/<int:pk>/hls/master.m3u8", hls_asset, {"asset": "master.m3u8"}, name="video_hls_manifest"),
    path("videos/<int:pk>/hls/<path:asset>", hls_asset, name="video_hls_asset"),
    path("django-admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("", include("apps.discovery.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("channels/", include("apps.channels.urls")),
    path("videos/", include("apps.videos.urls")),
    path("interactions/", include("apps.interactions.urls")),
    path("playlists/", include("apps.playlists.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("dashboard/", include("apps.analytics.urls")),
    path("studio/", include("apps.moderation.urls")),
    path("health/", TemplateView.as_view(template_name="health.html"), name="health"),
]
handler404 = "config.views.not_found"
handler500 = "config.views.server_error"
