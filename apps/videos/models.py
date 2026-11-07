from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from apps.channels.models import Channel


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=45, unique=True)

    def __str__(self):
        return self.name


class Video(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "عام"
        UNLISTED = "unlisted", "غير مدرج"
        PRIVATE = "private", "خاص"

    class Status(models.TextChoices):
        PROCESSING = "processing", "قيد المعالجة"
        READY = "ready", "جاهز"
        FAILED = "failed", "فشل"
        REMOVED = "removed", "محذوف"

    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="videos")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="videos")
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=5000, blank=True)
    video_file = models.FileField(upload_to="videos/source/%Y/%m/", max_length=500)
    thumbnail = models.ImageField(upload_to="videos/thumbnails/%Y/%m/", blank=True)
    hls_manifest = models.FileField(upload_to="videos/hls/%Y/%m/", blank=True, max_length=500)
    tags = models.ManyToManyField(Tag, through="VideoTag", blank=True, related_name="videos")
    visibility = models.CharField(max_length=12, choices=Visibility.choices, default=Visibility.PUBLIC)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROCESSING, db_index=True)
    comments_enabled = models.BooleanField(default=True)
    is_short = models.BooleanField(default=False, db_index=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    views_count = models.PositiveBigIntegerField(default=0, db_index=True)
    likes_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-created_at")
        indexes = [models.Index(fields=("visibility", "status", "published_at")),
                   models.Index(fields=("category", "published_at")),
                   models.Index(fields=("is_short", "published_at"))]

    def get_absolute_url(self):
        return reverse("video_detail", kwargs={"pk": self.pk})

    @property
    def duration_label(self):
        seconds = self.duration_seconds or 0
        return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}" if seconds >= 3600 else f"{seconds // 60:02d}:{seconds % 60:02d}"

    @property
    def is_vertical(self):
        return bool(self.height and self.width and self.height > self.width)

    def can_be_viewed_by(self, user, *, unlisted_token=False):
        if self.status != self.Status.READY or self.visibility == self.Visibility.PRIVATE and not (user.is_authenticated and user.pk == self.channel.owner_id):
            return False
        if self.visibility == self.Visibility.UNLISTED and not unlisted_token and not (user.is_authenticated and user.pk == self.channel.owner_id):
            return False
        return not self.channel.is_suspended

    def __str__(self):
        return self.title


class VideoTag(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("video", "tag"), name="uniq_video_tag")]


class VideoProcessingJob(models.Model):
    class State(models.TextChoices):
        QUEUED = "queued", "قيد الانتظار"
        RUNNING = "running", "قيد التنفيذ"
        SUCCEEDED = "succeeded", "مكتمل"
        FAILED = "failed", "فشل"

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="processing_jobs")
    state = models.CharField(max_length=12, choices=State.choices, default=State.QUEUED, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("state", "created_at"))]


class VideoRendition(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="renditions")
    quality = models.PositiveSmallIntegerField()
    file = models.FileField(upload_to="videos/renditions/%Y/%m/", max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("quality",)
        constraints = [models.UniqueConstraint(fields=("video", "quality"), name="uniq_video_rendition")]
