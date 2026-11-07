from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Channel(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="channel")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True)
    description = models.TextField(max_length=2000, blank=True)
    avatar = models.ImageField(upload_to="channels/avatars/%Y/%m/", blank=True)
    banner = models.ImageField(upload_to="channels/banners/%Y/%m/", blank=True)
    is_suspended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=("name",)), models.Index(fields=("created_at",))]

    def save(self, *args, **kwargs):
        old_name = type(self).objects.filter(pk=self.pk).values_list("name", flat=True).first() if self.pk else None
        if not self.slug or old_name is not None and old_name != self.name:
            base = slugify(self.name) or f"channel-{self.owner_id or 'new'}"
            candidate, index = base[:80], 1
            while Channel.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                index += 1
                candidate = f"{base[:78]}-{index}"
            self.slug = candidate
        super().save(*args, **kwargs)

    @property
    def subscriber_count(self):
        return getattr(self, "annotated_subscriber_count", self.subscriptions.count())

    def get_absolute_url(self):
        return reverse("channel_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.name


class Subscription(models.Model):
    subscriber = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="subscriptions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("subscriber", "channel"), name="uniq_channel_subscription")]
        indexes = [models.Index(fields=("channel", "created_at")), models.Index(fields=("subscriber", "created_at"))]

    def __str__(self):
        return f"{self.subscriber} → {self.channel}"
