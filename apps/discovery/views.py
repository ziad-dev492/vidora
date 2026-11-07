from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from apps.channels.models import Subscription
from apps.videos.models import Category, Video


def public_videos():
    return Video.objects.filter(status=Video.Status.READY, visibility=Video.Visibility.PUBLIC, channel__is_suspended=False).select_related("channel", "category").prefetch_related("tags").annotate(annotated_subscriber_count=Count("channel__subscriptions")).order_by("-published_at", "-pk")


def home(request):
    videos = public_videos()
    category = request.GET.get("category")
    if category:
        videos = videos.filter(category__slug=category)
    page = Paginator(videos, 24).get_page(request.GET.get("page"))
    return render(request, "home.html", {"video_list": page, "page_obj": page, "category_list": Category.objects.filter(is_active=True), "selected_category": category})


def search(request):
    query = request.GET.get("q", "").strip()[:120]
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "relevance")
    videos = public_videos()
    if query:
        videos = videos.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(tags__name__icontains=query) | Q(channel__name__icontains=query)).distinct()
    else:
        videos = videos.none()
    if category:
        videos = videos.filter(category__slug=category)
    if sort == "newest":
        videos = videos.order_by("-published_at")
    elif sort == "views":
        videos = videos.order_by("-views_count", "-published_at")
    page = Paginator(videos, 24).get_page(request.GET.get("page"))
    channels = []
    if query:
        from apps.channels.models import Channel
        channels = Channel.objects.filter(is_suspended=False).filter(Q(name__icontains=query) | Q(description__icontains=query)).annotate(annotated_subscriber_count=Count("subscriptions")).order_by("-annotated_subscriber_count")[:10]
    return render(request, "list_page.html", {"page_title": "نتائج البحث", "video_list": page, "page_obj": page, "search_query": query, "channel_list": channels, "category_list": Category.objects.filter(is_active=True), "selected_category": category, "sort": sort})


def category(request, slug):
    selected = get_object_or_404(Category, slug=slug, is_active=True)
    page = Paginator(public_videos().filter(category=selected), 24).get_page(request.GET.get("page"))
    return render(request, "home.html", {"video_list": page, "page_obj": page, "category_list": Category.objects.filter(is_active=True), "selected_category": slug, "page_title": selected.name})


def shorts(request):
    videos = public_videos().filter(is_short=True, height__gt=0).order_by("-published_at")
    page = Paginator(videos, 12).get_page(request.GET.get("page"))
    return render(request, "shorts.html", {"video_list": page, "page_obj": page})

@login_required
def subscriptions(request):
    channel_ids = Subscription.objects.filter(subscriber=request.user).values_list("channel_id", flat=True)
    page = Paginator(public_videos().filter(channel_id__in=channel_ids), 24).get_page(request.GET.get("page"))
    return render(request, "list_page.html", {"page_title": "الاشتراكات", "video_list": page, "page_obj": page})
