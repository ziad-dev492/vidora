from django.conf import settings
from django.db import models
from apps.videos.models import Video


class Playlist(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlists")
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self):
        return self.title


class PlaylistVideo(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="items")
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="playlist_items")
    position = models.PositiveIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position", "added_at")
        constraints = [models.UniqueConstraint(fields=("playlist", "video"), name="uniq_playlist_video")]
        indexes = [models.Index(fields=("playlist", "position"))]


class WatchHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watch_history")
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="history_entries")
    watched_at = models.DateTimeField(auto_now=True)
    watch_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-watched_at",)
        constraints = [models.UniqueConstraint(fields=("user", "video"), name="uniq_user_video_history")]
        indexes = [models.Index(fields=("user", "-watched_at"))]


class WatchLater(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watch_later")
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="saved_by")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-added_at",)
        constraints = [models.UniqueConstraint(fields=("user", "video"), name="uniq_user_watch_later")]
