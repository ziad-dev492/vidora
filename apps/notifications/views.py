from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Notification

@login_required
def notification_list(request):
    rows = Notification.objects.filter(recipient=request.user)
    return render(request, "notifications.html", {"page_title": "الإشعارات", "notifications": rows[:100]})

@login_required
@require_POST
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=("is_read",))
    return redirect(notification.target_url or "notifications")
