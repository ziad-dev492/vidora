from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.channels.models import Channel
from apps.channels.api import ChannelSerializer
from .models import Video
from .serializers import VideoSerializer

class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description", "tags__name", "channel__name"]
    ordering_fields = ["published_at", "views_count"]
    ordering = ["-published_at"]
    def get_queryset(self):
        return Video.objects.filter(status=Video.Status.READY, visibility=Video.Visibility.PUBLIC, channel__is_suspended=False).select_related("channel", "category").prefetch_related("tags").distinct()
