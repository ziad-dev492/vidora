from django.conf import settings
from django.db import models
from django.db.models import Q


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_notifications")
    kind = models.CharField(max_length=24)
    message = models.CharField(max_length=240)
    target_url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("recipient", "is_read", "-created_at"))]


class Report(models.Model):
    class State(models.TextChoices):
        OPEN = "open", "مفتوح"
        REVIEWING = "reviewing", "قيد المراجعة"
        RESOLVED = "resolved", "تمت المعالجة"
        DISMISSED = "dismissed", "مرفوض"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    video = models.ForeignKey("videos.Video", on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
    comment = models.ForeignKey("interactions.Comment", on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
    reason = models.CharField(max_length=40)
    details = models.TextField(max_length=1000, blank=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.OPEN, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=(Q(video__isnull=False, comment__isnull=True) | Q(video__isnull=True, comment__isnull=False)), name="report_exactly_one_target")]
        indexes = [models.Index(fields=("state", "-created_at"))]


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80, blank=True)
    target_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("-created_at",)), models.Index(fields=("action", "created_at"))]
