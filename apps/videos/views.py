import hashlib
import hmac
import mimetypes
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import F, Prefetch, Q
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from apps.core.rate_limit import rate_limit
from .forms import VideoUploadForm
from .models import Video, VideoProcessingJob, Tag
from apps.channels.models import Channel
from apps.interactions.models import VideoLike, VideoView, Comment
from apps.playlists.models import WatchHistory
from .tasks import process_video


def _delete_storage_prefix(prefix):
    try:
        directories, files = default_storage.listdir(prefix)
    except (FileNotFoundError, NotImplementedError):
        return
    for name in files:
        default_storage.delete(f"{prefix}/{name}")
    for name in directories:
        _delete_storage_prefix(f"{prefix}/{name}")


def _visible_queryset(user):
    qs = Video.objects.filter(status=Video.Status.READY, channel__is_suspended=False).select_related("channel", "category").prefetch_related("tags", "renditions")
    if user.is_authenticated:
        return qs.filter(Q(visibility=Video.Visibility.PUBLIC) | Q(channel__owner=user, visibility__in=(Video.Visibility.UNLISTED, Video.Visibility.PRIVATE)))
    return qs.filter(visibility=Video.Visibility.PUBLIC)


@login_required
@rate_limit(10, 3600)
@require_http_methods(["GET", "POST"])
def upload_video(request):
    channel = getattr(request.user, "channel", None)
    if channel is None:
        messages.info(request, "أنشئ قناة قبل رفع الفيديو.")
        return redirect("channel_setup")
    form = VideoUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        video = form.save(commit=False)
        video.channel = channel
        video.status = Video.Status.PROCESSING
        video.save()
        names = [s.strip().lstrip("#")[:40] for s in form.cleaned_data.get("tags_text", "").split(",") if s.strip()][:12]
        for tag_name in names:
            tag, _ = Tag.objects.get_or_create(name=tag_name, defaults={"slug": f"tag-{hashlib.sha1(tag_name.lower().encode()).hexdigest()[:12]}"})
            video.tags.add(tag)
        job = VideoProcessingJob.objects.create(video=video)
        transaction.on_commit(lambda: _queue_processing(video.pk))
        messages.success(request, "اكتمل رفع الملف؛ الفيديو قيد المعالجة ولن يظهر قبل جاهزيته.")
        return redirect("dashboard")
    return render(request, "upload.html", {"form": form, "page_title": "رفع فيديو"})


@login_required
@rate_limit(20, 3600)
@require_http_methods(["GET", "POST"])
def edit_video(request, pk):
    video = get_object_or_404(Video.objects.select_related("channel"), pk=pk, channel__owner=request.user)
    form = VideoUploadForm(request.POST or None, request.FILES or None, instance=video)
    form.fields["video_file"].required = False
    if request.method == "POST" and form.is_valid():
        changed_file = bool(form.cleaned_data.get("video_file"))
        changed_thumbnail = bool(request.FILES.get("thumbnail"))
        old_file = video.video_file.name
        old_thumbnail = video.thumbnail.name
        old_renditions = list(video.renditions.values_list("file", flat=True))
        updated = form.save(commit=False)
        if changed_file:
            updated.status = Video.Status.PROCESSING
            updated.published_at = None
            updated.hls_manifest = ""
        updated.save()
        if changed_file:
            for name in [old_file, *old_renditions]:
                if name:
                    default_storage.delete(name)
            video.renditions.all().delete()
            _delete_storage_prefix(f"videos/hls/{video.pk}")
            transaction.on_commit(lambda: _queue_processing(updated.pk))
        elif changed_thumbnail and old_thumbnail and old_thumbnail != updated.thumbnail.name:
            default_storage.delete(old_thumbnail)
        messages.success(request, "تم حفظ التعديلات.")
        return redirect("video_detail", pk=video.pk)
    return render(request, "upload.html", {"form": form, "video": video, "page_title": "تعديل الفيديو"})


def video_detail(request, pk):
    video = get_object_or_404(Video.objects.select_related("channel", "category").prefetch_related("tags", "renditions"), pk=pk, channel__is_suspended=False)
    owner = request.user.is_authenticated and video.channel.owner_id == request.user.pk
    if video.status != Video.Status.READY and not owner:
        raise Http404
    if video.visibility == Video.Visibility.PRIVATE and not owner:
        raise Http404
    if video.visibility == Video.Visibility.UNLISTED and not owner:
        # Unlisted content is accessible to those holding its opaque URL, but not indexed or listed.
        pass
    if not owner and video.status != Video.Status.READY:
        raise Http404
    liked = VideoLike.objects.filter(user=request.user, video=video, value=VideoLike.Value.LIKE).exists() if request.user.is_authenticated else False
    disliked = VideoLike.objects.filter(user=request.user, video=video, value=VideoLike.Value.DISLIKE).exists() if request.user.is_authenticated else False
    subscribed = request.user.is_authenticated and video.channel.subscriptions.filter(subscriber=request.user).exists()
    saved = request.user.is_authenticated and video.saved_by.filter(user=request.user).exists()
    comments = Comment.objects.filter(video=video, is_hidden=False, parent__isnull=True).select_related("author").prefetch_related(Prefetch("replies", queryset=Comment.objects.filter(is_hidden=False).select_related("author"))) if video.comments_enabled else Comment.objects.none()
    comments = comments[:100]
    suggestions = _visible_queryset(request.user).exclude(pk=video.pk).filter(Q(category=video.category) | Q(tags__in=video.tags.all())).distinct()[:8]
    playlists = request.user.playlists.all() if request.user.is_authenticated else []
    return render(request, "video_detail.html", {"video": video, "comments": comments, "recommendations": suggestions, "liked": liked, "disliked": disliked, "subscribed": subscribed, "saved": saved, "is_owner": owner, "playlists": playlists})


def _record_view(request, video):
    day = timezone.localdate()
    defaults = {"viewer": request.user if request.user.is_authenticated else None, "view_day": day}
    if not request.user.is_authenticated:
        ip = request.META.get("REMOTE_ADDR", "")
        material = f"{ip}:{day.isoformat()}".encode()
        defaults["visitor_hash"] = hmac.new(settings.SECRET_KEY.encode(), material, hashlib.sha256).hexdigest()
    try:
        with transaction.atomic():
            VideoView.objects.create(video=video, **defaults)
            Video.objects.filter(pk=video.pk).update(views_count=F("views_count") + 1)
    except IntegrityError:
        pass
    if request.user.is_authenticated:
        WatchHistory.objects.update_or_create(user=request.user, video=video, defaults={"watched_at": timezone.now()})


@require_GET
def stream_video(request, pk):
    video = get_object_or_404(Video.objects.select_related("channel"), pk=pk)
    owner = request.user.is_authenticated and video.channel.owner_id == request.user.pk
    if video.status != Video.Status.READY and not owner or video.visibility == Video.Visibility.PRIVATE and not owner or video.channel.is_suspended:
        raise Http404
    try:
        quality = request.GET.get("quality", "")
        rendition = video.renditions.filter(quality=int(quality)).first() if quality.isdigit() else None
        media_file = rendition.file if rendition else video.video_file
        source = media_file.storage.open(media_file.name, "rb")
        source.seek(0, 2)
        size = source.tell()
        range_header = request.headers.get("Range", "")
        start, end = 0, size - 1
        status = 200
        if range_header.startswith("bytes="):
            try:
                left, right = range_header[6:].split(",", 1)[0].split("-")
                if left:
                    start = int(left)
                else:
                    length = int(right)
                    start = max(0, size - length)
                if right and left:
                    end = min(size - 1, int(right))
                if start > end or start >= size:
                    raise ValueError
                status = 206
            except (ValueError, IndexError):
                source.close()
                return HttpResponse(status=416, headers={"Content-Range": f"bytes */{size}"})
        source.seek(start)
        remaining = end - start + 1
        def chunks():
            nonlocal remaining
            try:
                while remaining > 0:
                    data = source.read(min(1024 * 1024, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
            finally:
                source.close()
        content_type = mimetypes.guess_type(media_file.name)[0] or "application/octet-stream"
        response = StreamingHttpResponse(chunks(), status=status, content_type=content_type)
        response["Accept-Ranges"] = "bytes"
        response["Content-Length"] = str(end - start + 1)
        if status == 206:
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
        response["Cache-Control"] = "private, no-store"
        _record_view(request, video)
        return response
    except FileNotFoundError:
        raise Http404


@login_required
@require_http_methods(["POST"])
def delete_video(request, pk):
    video = get_object_or_404(Video.objects.select_related("channel"), pk=pk, channel__owner=request.user)
    names = [video.video_file.name, video.thumbnail.name, video.hls_manifest.name]
    names.extend(video.renditions.values_list("file", flat=True))
    _delete_storage_prefix(f"videos/hls/{video.pk}")
    for name in set(filter(None, names)):
        try:
            default_storage.delete(name)
        except OSError:
            pass
    video.delete()
    messages.success(request, "تم حذف الفيديو وملفاته.")
    return redirect("dashboard")


@login_required
@rate_limit(5, 3600)
@require_http_methods(["POST"])
def retry_video_processing(request, pk):
    video = get_object_or_404(Video.objects.select_related("channel"), pk=pk, channel__owner=request.user, status=Video.Status.FAILED)
    job = VideoProcessingJob.objects.create(video=video)
    video.status = Video.Status.PROCESSING
    video.save(update_fields=("status",))
    transaction.on_commit(lambda: _queue_processing(video.pk))
    messages.info(request, f"أعيدت جدولة المعالجة (المهمة #{job.pk}).")
    return redirect("dashboard")


def _queue_processing(video_id):
    try:
        process_video.delay(video_id)
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Could not queue video %s; check Redis and the Celery worker", video_id)
        job = VideoProcessingJob.objects.filter(video_id=video_id).order_by("-created_at").first()
        if job:
            job.state = VideoProcessingJob.State.FAILED
            job.error_message = f"تعذر إرسال مهمة Celery. تحقق من تشغيل Redis والعامل ثم أعد المحاولة. ({str(exc)[:300]})"
            job.finished_at = timezone.now()
            job.save(update_fields=("state", "error_message", "finished_at"))
        Video.objects.filter(pk=video_id).update(status=Video.Status.FAILED)
