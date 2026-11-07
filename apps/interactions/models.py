from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.videos.models import Video


class VideoView(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="view_events")
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="video_views")
    visitor_hash = models.CharField(max_length=64, blank=True)
    view_day = models.DateField(default=__import__("django.utils.timezone", fromlist=["localdate"]).localdate)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("video", "viewer", "view_day"), condition=Q(viewer__isnull=False), name="uniq_user_video_daily_view"),
            models.UniqueConstraint(fields=("video", "visitor_hash", "view_day"), condition=~Q(visitor_hash=""), name="uniq_anon_video_daily_view"),
        ]
        indexes = [models.Index(fields=("video", "viewed_at")), models.Index(fields=("viewer", "viewed_at"))]


class VideoLike(models.Model):
    class Value(models.IntegerChoices):
        DISLIKE = -1, "عدم إعجاب"
        LIKE = 1, "إعجاب"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_likes")
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="user_likes")
    value = models.SmallIntegerField(choices=Value.choices, default=Value.LIKE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "video"), name="uniq_user_video_like")]
        indexes = [models.Index(fields=("video", "value"))]


class Comment(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    body = models.TextField(max_length=3000)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("video", "created_at")), models.Index(fields=("author", "created_at"))]

    def __str__(self):
        return f"{self.author}: {self.body[:50]}"
