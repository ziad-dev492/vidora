from django.conf import settings
from apps.notifications.models import Notification


def site_settings(request):
    unread = 0
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        unread = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return {"brand_name": settings.BRAND_NAME, "unread_notification_count": unread}
