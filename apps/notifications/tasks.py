from celery import shared_task
from django.urls import reverse
from apps.channels.models import Subscription
from .models import Notification

@shared_task(ignore_result=True)
def notify_subscribers(video_id):
    from apps.videos.models import Video
    video = Video.objects.select_related("channel").filter(pk=video_id, status=Video.Status.READY, visibility=Video.Visibility.PUBLIC).first()
    if not video:
        return 0
    base_url = reverse("video_detail", kwargs={"pk": video.pk})
    batch, total = [], 0
    for user_id in Subscription.objects.filter(channel=video.channel).values_list("subscriber_id", flat=True).iterator(chunk_size=500):
        batch.append(Notification(recipient_id=user_id, kind="new_video", message=f"نشرت {video.channel.name} فيديو جديدًا: {video.title[:150]}", target_url=base_url))
        if len(batch) >= 500:
            Notification.objects.bulk_create(batch, ignore_conflicts=True)
            total += len(batch)
            batch.clear()
    if batch:
        Notification.objects.bulk_create(batch, ignore_conflicts=True)
        total += len(batch)
    return total
