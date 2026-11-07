from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from apps.core.rate_limit import rate_limit
from apps.accounts.models import User
from apps.channels.models import Channel
from apps.notifications.models import AuditLog, Report
from apps.videos.models import Category, Video
from apps.interactions.models import Comment


@staff_member_required
def admin_dashboard(request):
    stats = {"users": User.objects.count(), "channels": Channel.objects.count(), "videos": Video.objects.count(), "reports": Report.objects.filter(state=Report.State.OPEN).count()}
    latest_reports = Report.objects.select_related("reporter", "video", "comment").order_by("-created_at")[:20]
    categories = Category.objects.annotate(video_count=Count("videos")).order_by("sort_order", "name")
    category_data = [{"name": item.name, "count": item.video_count} for item in categories]
    channels = Channel.objects.select_related("owner").annotate(annotated_subscriber_count=Count("subscriptions")).order_by("-created_at")[:20]
    return render(request, "admin_dashboard.html", {"stats": stats, "reports": latest_reports, "category_list": categories, "category_data": category_data, "users": User.objects.order_by("-date_joined")[:20], "channel_list": channels, "audit_logs": AuditLog.objects.select_related("actor")[:20]})


@staff_member_required
@require_POST
@rate_limit(100, 3600)
def update_report(request, pk):
    report = get_object_or_404(Report, pk=pk)
    state = request.POST.get("state")
    if state in Report.State.values:
        report.state = state
        report.reviewed_at = timezone.now()
        report.save(update_fields=("state", "reviewed_at"))
        target = report.video or (report.comment.video if report.comment_id else None)
        if request.POST.get("hide_target") == "on":
            if report.video_id:
                Video.objects.filter(pk=report.video_id).update(status=Video.Status.REMOVED)
            elif report.comment_id:
                Comment.objects.filter(pk=report.comment_id).update(is_hidden=True)
        AuditLog.objects.create(actor=request.user, action=f"report.{state}", target_type="report", target_id=str(report.pk), metadata={"target": target.pk if target else None, "hidden": request.POST.get("hide_target") == "on"})
        messages.success(request, "تم حفظ قرار المراجعة.")
    return redirect("admin_dashboard")


@staff_member_required
@require_POST
@rate_limit(60, 3600)
def suspend_channel(request, pk):
    channel = get_object_or_404(Channel, pk=pk)
    channel.is_suspended = not channel.is_suspended
    channel.save(update_fields=("is_suspended",))
    AuditLog.objects.create(actor=request.user, action="channel.suspension_toggled", target_type="channel", target_id=str(channel.pk), metadata={"suspended": channel.is_suspended})
    return redirect("admin_dashboard")


@staff_member_required
@require_POST
@rate_limit(60, 3600)
def toggle_user_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk or user.is_superuser:
        messages.error(request, "لا يمكن تعطيل حسابك أو حساب مدير أعلى صلاحية.")
        return redirect("admin_dashboard")
    user.is_active = not user.is_active
    user.save(update_fields=("is_active",))
    AuditLog.objects.create(actor=request.user, action="user.active_toggled", target_type="user", target_id=str(user.pk), metadata={"active": user.is_active})
    messages.success(request, "تم تحديث صلاحية الحساب.")
    return redirect("admin_dashboard")


@staff_member_required
@require_POST
@rate_limit(60, 3600)
def manage_category(request):
    action = request.POST.get("action")
    if action == "create":
        name = request.POST.get("name", "").strip()[:60]
        slug = slugify(request.POST.get("slug", "").strip())[:70]
        if not name or not slug:
            messages.error(request, "أدخل اسم التصنيف ورابطًا لاتينيًا صالحًا.")
        elif Category.objects.filter(name=name).exists() or Category.objects.filter(slug=slug).exists():
            messages.error(request, "اسم التصنيف أو رابطه مستخدم مسبقًا.")
        else:
            category = Category.objects.create(name=name, slug=slug)
            AuditLog.objects.create(actor=request.user, action="category.created", target_type="category", target_id=str(category.pk))
            messages.success(request, "تم إنشاء التصنيف.")
    elif action == "toggle":
        category = get_object_or_404(Category, pk=request.POST.get("category_id"))
        category.is_active = not category.is_active
        category.save(update_fields=("is_active",))
        AuditLog.objects.create(actor=request.user, action="category.active_toggled", target_type="category", target_id=str(category.pk), metadata={"active": category.is_active})
        messages.success(request, "تم تحديث التصنيف.")
    return redirect("admin_dashboard")
