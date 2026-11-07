from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from apps.core.rate_limit import rate_limit
from apps.channels.models import Channel, Subscription
from apps.notifications.models import Notification, Report
from apps.videos.models import Video
from .models import Comment, VideoLike


@login_required
@rate_limit(180, 3600)
@require_POST
def like_video(request, pk):
    video = get_object_or_404(Video.objects.select_related("channel"), pk=pk, status=Video.Status.READY)
    if video.visibility == Video.Visibility.PRIVATE and video.channel.owner_id != request.user.pk:
        return HttpResponseForbidden()
    existing = VideoLike.objects.filter(user=request.user, video=video).first()
    requested = VideoLike.Value.DISLIKE if request.POST.get("value") == "dislike" else VideoLike.Value.LIKE
    if existing and existing.value == requested:
        existing.delete()
        if requested == VideoLike.Value.LIKE:
            Video.objects.filter(pk=video.pk, likes_count__gt=0).update(likes_count=F("likes_count") - 1)
    else:
        was_like = bool(existing and existing.value == VideoLike.Value.LIKE)
        VideoLike.objects.update_or_create(user=request.user, video=video, defaults={"value": requested})
        if requested == VideoLike.Value.LIKE and not was_like:
            Video.objects.filter(pk=video.pk).update(likes_count=F("likes_count") + 1)
            if video.channel.owner_id != request.user.pk:
                Notification.objects.create(
                    recipient=video.channel.owner,
                    actor=request.user,
                    kind="like",
                    message=f"أعجب {request.user.username} بفيديو «{video.title[:90]}».",
                    target_url=video.get_absolute_url(),
                )
        elif was_like and requested != VideoLike.Value.LIKE:
            Video.objects.filter(pk=video.pk, likes_count__gt=0).update(likes_count=F("likes_count") - 1)
    return redirect("video_detail", pk=video.pk)


@login_required
@rate_limit(60, 3600)
@require_POST
def toggle_subscription(request, slug):
    channel = get_object_or_404(Channel, slug=slug, is_suspended=False)
    if channel.owner_id == request.user.pk:
        messages.error(request, "لا يمكنك الاشتراك في قناتك.")
        return redirect(channel.get_absolute_url())
    sub, created = Subscription.objects.get_or_create(subscriber=request.user, channel=channel)
    if not created:
        sub.delete()
    else:
        Notification.objects.create(recipient=channel.owner, actor=request.user, kind="subscriber", message=f"اشترك {request.user.username} في قناتك.", target_url=channel.get_absolute_url())
    return redirect(request.POST.get("next") or channel.get_absolute_url())


@login_required
@rate_limit(60, 3600)
@require_POST
def add_comment(request, pk):
    video = get_object_or_404(Video, pk=pk, status=Video.Status.READY, comments_enabled=True)
    if video.visibility == Video.Visibility.PRIVATE and video.channel.owner_id != request.user.pk:
        return HttpResponseForbidden()
    body = request.POST.get("body", "").strip()
    parent_id = request.POST.get("parent_id")
    if not body or len(body) > 3000:
        messages.error(request, "اكتب تعليقًا لا يتجاوز 3000 حرف.")
        return redirect("video_detail", pk=video.pk)
    parent = None
    if parent_id:
        parent = get_object_or_404(Comment, pk=parent_id, video=video, parent__isnull=True, is_hidden=False)
    comment = Comment.objects.create(video=video, author=request.user, parent=parent, body=body)
    recipient = parent.author if parent else video.channel.owner
    if recipient != request.user:
        Notification.objects.create(recipient=recipient, actor=request.user, kind="reply" if parent else "comment", message=f"{request.user.username} علّق على فيديو «{video.title[:90]}».", target_url=video.get_absolute_url())
    return redirect(video.get_absolute_url() + f"#comment-{comment.pk}")


@login_required
@rate_limit(60, 3600)
@require_POST
def edit_comment(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("video"), pk=pk, author=request.user)
    body = request.POST.get("body", "").strip()
    if not body or len(body) > 3000:
        messages.error(request, "اكتب تعليقًا لا يتجاوز 3000 حرف.")
    else:
        comment.body = body
        comment.save(update_fields=("body", "updated_at"))
        messages.success(request, "تم تحديث التعليق.")
    return redirect(comment.video.get_absolute_url() + f"#comment-{comment.pk}")


@login_required
@rate_limit(60, 3600)
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("video__channel"), pk=pk)
    if comment.author_id != request.user.pk and comment.video.channel.owner_id != request.user.pk and not request.user.is_staff:
        return HttpResponseForbidden()
    video_id = comment.video_id
    comment.delete()
    messages.success(request, "تم حذف التعليق.")
    return redirect("video_detail", pk=video_id)


@login_required
@rate_limit(10, 3600)
@require_POST
def report_content(request):
    kind = request.POST.get("target_type")
    reason = request.POST.get("reason", "other")[:40]
    details = request.POST.get("details", "").strip()[:1000]
    if kind == "comment":
        target = get_object_or_404(Comment, pk=request.POST.get("target_id"), is_hidden=False)
        Report.objects.create(reporter=request.user, comment=target, reason=reason, details=details)
        destination = target.video.get_absolute_url()
    else:
        target = get_object_or_404(Video, pk=request.POST.get("target_id"), status=Video.Status.READY)
        Report.objects.create(reporter=request.user, video=target, reason=reason, details=details)
        destination = target.get_absolute_url()
    messages.success(request, "وصل البلاغ إلى فريق الإشراف.")
    return redirect(destination)
