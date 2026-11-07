from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import redirect, render
from django.utils import timezone
from apps.channels.models import Subscription
from apps.interactions.models import VideoLike
from apps.videos.models import Video

@login_required
def dashboard(request):
    channel = getattr(request.user, "channel", None)
    if channel is None:
        return redirect("channel_setup")
    videos = Video.objects.filter(channel=channel).select_related("category").order_by("-created_at")
    totals = videos.aggregate(views=Sum("views_count"), likes=Sum("likes_count"))
    cutoff = timezone.now() - timedelta(days=30)
    chart = list(videos.filter(view_events__viewed_at__gte=cutoff).annotate(day=TruncDate("view_events__viewed_at")).values("day").annotate(count=Count("view_events")).order_by("day"))
    return render(request, "dashboard.html", {"channel": channel, "video_list": videos[:50], "stats": {"views": totals["views"] or 0, "likes": totals["likes"] or 0, "subscribers": Subscription.objects.filter(channel=channel).count(), "videos": videos.count()}, "chart_data": chart})

@login_required
def video_manage(request):
    channel = getattr(request.user, "channel", None)
    if channel is None:
        return redirect("channel_setup")
    return render(request, "list_page.html", {"page_title": "إدارة الفيديوهات", "video_list": Video.objects.filter(channel=channel).order_by("-created_at")})
