from django.shortcuts import get_object_or_404, render
from django.db.models import Count
from .models import Channel
from apps.videos.models import Video


def channel_detail(request, slug):
    channel = get_object_or_404(Channel.objects.annotate(annotated_subscriber_count=Count("subscriptions")), slug=slug, is_suspended=False)
    videos = Video.objects.filter(channel=channel, status=Video.Status.READY, visibility=Video.Visibility.PUBLIC).select_related("channel", "category").order_by("-published_at")
    return render(request, "channel_detail.html", {"channel": channel, "video_list": videos[:48]})
