from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.core.rate_limit import rate_limit
from .models import Playlist, PlaylistVideo, WatchHistory, WatchLater
from apps.videos.models import Video
from apps.interactions.models import VideoLike


@login_required
@rate_limit(20, 3600)
def playlist_list(request):
    playlists = Playlist.objects.filter(owner=request.user).annotate(item_count=Count("items")).prefetch_related("items__video__channel")
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if not title or len(title) > 100:
            messages.error(request, "أدخل اسم قائمة لا يتجاوز 100 حرف.")
        else:
            playlist = Playlist.objects.create(owner=request.user, title=title, is_public=request.POST.get("is_public") == "on")
            return redirect("playlist_detail", pk=playlist.pk)
    return render(request, "list_page.html", {"page_title": "قوائم التشغيل", "playlists": playlists})


def playlist_detail(request, pk):
    playlist = get_object_or_404(Playlist.objects.select_related("owner").prefetch_related("items__video__channel"), pk=pk)
    is_owner = request.user.is_authenticated and playlist.owner_id == request.user.pk
    if not playlist.is_public and not is_owner:
        return HttpResponseForbidden()
    items = playlist.items.select_related("video__channel", "video__category").prefetch_related("video__tags")
    if not is_owner:
        items = items.filter(video__status=Video.Status.READY, video__visibility=Video.Visibility.PUBLIC, video__channel__is_suspended=False)
    return render(request, "list_page.html", {"page_title": playlist.title, "playlist": playlist, "video_list": [item.video for item in items], "is_playlist_owner": is_owner})


@login_required
@rate_limit(60, 3600)
@require_POST
def add_to_playlist(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk, owner=request.user)
    video = get_object_or_404(Video, pk=request.POST.get("video_id"), status=Video.Status.READY, visibility=Video.Visibility.PUBLIC, channel__is_suspended=False)
    next_position = playlist.items.aggregate(value=Max("position"))["value"]
    PlaylistVideo.objects.get_or_create(playlist=playlist, video=video, defaults={"position": (next_position or 0) + 1})
    messages.success(request, "أضيف الفيديو إلى القائمة.")
    return redirect(playlist_detail, pk=playlist.pk)


@login_required
@rate_limit(30, 3600)
@require_POST
def manage_playlist(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk, owner=request.user)
    action = request.POST.get("action")
    if action == "delete":
        playlist.delete()
        messages.success(request, "تم حذف قائمة التشغيل.")
        return redirect("playlist_list")
    if action == "remove":
        PlaylistVideo.objects.filter(playlist=playlist, video_id=request.POST.get("video_id")).delete()
        messages.success(request, "تمت إزالة الفيديو من القائمة.")
    elif action == "update":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        if not title or len(title) > 100 or len(description) > 500:
            messages.error(request, "تحقق من العنوان (100 حرف) والوصف (500 حرف).")
        else:
            playlist.title, playlist.description = title, description
            playlist.is_public = request.POST.get("is_public") == "on"
            playlist.save(update_fields=("title", "description", "is_public", "updated_at"))
            messages.success(request, "تم حفظ إعدادات القائمة.")
    return redirect("playlist_detail", pk=playlist.pk)


@login_required
@rate_limit(120, 3600)
@require_POST
def toggle_watch_later(request, pk):
    video = get_object_or_404(Video, pk=pk, status=Video.Status.READY, channel__is_suspended=False)
    if video.visibility == Video.Visibility.PRIVATE and video.channel.owner_id != request.user.pk:
        return HttpResponseForbidden()
    item, created = WatchLater.objects.get_or_create(user=request.user, video=video)
    if not created:
        item.delete()
    return redirect(request.POST.get("next") or video.get_absolute_url())


@login_required
def watch_later_list(request):
    access = Q(visibility__in=(Video.Visibility.PUBLIC, Video.Visibility.UNLISTED)) | Q(channel__owner=request.user, visibility=Video.Visibility.PRIVATE)
    videos = Video.objects.filter(saved_by__user=request.user, status=Video.Status.READY, channel__is_suspended=False).filter(access).select_related("channel", "category").order_by("-saved_by__added_at")
    return render(request, "list_page.html", {"page_title": "المشاهدة لاحقًا", "video_list": videos})


@login_required
def watch_history(request):
    entries = WatchHistory.objects.filter(user=request.user).select_related("video__channel", "video__category", "video__channel__owner").prefetch_related("video__tags")
    visible = [entry for entry in entries[:100] if entry.video.visibility != Video.Visibility.PRIVATE or entry.video.channel.owner_id == request.user.pk]
    return render(request, "list_page.html", {"page_title": "سجل المشاهدة", "history_entries": visible, "video_list": [entry.video for entry in visible]})


@login_required
@rate_limit(60, 3600)
@require_POST
def clear_history(request):
    if request.POST.get("video_id"):
        WatchHistory.objects.filter(user=request.user, video_id=request.POST["video_id"]).delete()
    else:
        WatchHistory.objects.filter(user=request.user).delete()
    messages.success(request, "تم تحديث سجل المشاهدة.")
    return redirect("history")


@login_required
def liked_videos(request):
    access = Q(visibility__in=(Video.Visibility.PUBLIC, Video.Visibility.UNLISTED)) | Q(channel__owner=request.user, visibility=Video.Visibility.PRIVATE)
    videos = Video.objects.filter(user_likes__user=request.user, user_likes__value=VideoLike.Value.LIKE, status=Video.Status.READY, channel__is_suspended=False).filter(access).select_related("channel", "category").prefetch_related("tags").order_by("-user_likes__created_at")
    return render(request, "list_page.html", {"page_title": "الفيديوهات التي أعجبتني", "video_list": videos})
