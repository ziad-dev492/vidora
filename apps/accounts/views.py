import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from apps.core.rate_limit import rate_limit
from .forms import SignUpForm, ProfileForm, ChannelForm
from .models import User
from apps.channels.models import Channel

logger = logging.getLogger(__name__)
EMAIL_TOKEN_SALT = "vidora.accounts.email.verify.v1"


def _send_verification(request, user):
    token = signing.dumps({"pk": user.pk, "email": user.email}, salt=EMAIL_TOKEN_SALT)
    url = request.build_absolute_uri(reverse("email_verify", kwargs={"token": token}))
    return send_mail("تحقق من بريدك في Vidora", f"افتح الرابط خلال 24 ساعة لتأكيد بريدك:\n{url}\n", settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


@ensure_csrf_cookie
@rate_limit(5, 3600)
def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        try:
            _send_verification(request, user)
            messages.info(request, "تحقق من بريدك لتأكيد عنوان البريد الإلكتروني.")
        except Exception:
            logger.exception("Unable to send verification email for user %s", user.pk)
            messages.warning(request, "أُنشئ الحساب، لكن تعذر إرسال رسالة التحقق الآن.")
        messages.success(request, "تم إنشاء حسابك بنجاح.")
        return redirect("home")
    return render(request, "form_page.html", {"form": form, "page_title": "إنشاء حساب", "submit_label": "إنشاء الحساب", "form_kind": "signup"})


@login_required
@require_http_methods(["GET", "POST"])
def profile_settings(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, "تم حفظ إعدادات الملف الشخصي.")
        if not user.email_verified:
            messages.info(request, "يمكنك إرسال رسالة تحقق جديدة إلى بريدك.")
        return redirect("settings")
    return render(request, "form_page.html", {"form": form, "page_title": "إعدادات الحساب", "submit_label": "حفظ", "form_kind": "settings", "email_verified": request.user.email_verified})


@login_required
@rate_limit(3, 3600)
@require_http_methods(["POST"])
def resend_verification(request):
    if request.user.email_verified:
        messages.info(request, "تم التحقق من بريدك بالفعل.")
    else:
        try:
            _send_verification(request, request.user)
            messages.success(request, "أُرسلت رسالة تحقق جديدة.")
        except Exception:
            logger.exception("Unable to resend verification email for user %s", request.user.pk)
            messages.error(request, "تعذر إرسال الرسالة الآن.")
    return redirect("settings")


def verify_email(request, token):
    try:
        payload = signing.loads(token, salt=EMAIL_TOKEN_SALT, max_age=24 * 60 * 60)
    except (signing.BadSignature, signing.SignatureExpired):
        messages.error(request, "رابط التحقق غير صالح أو انتهت صلاحيته.")
        return redirect("home")
    user = get_object_or_404(User, pk=payload.get("pk"), email=payload.get("email"))
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=("email_verified",))
        messages.success(request, "تم التحقق من بريدك الإلكتروني.")
    return redirect("home")


@login_required
@require_http_methods(["GET", "POST"])
def create_or_edit_channel(request):
    instance = getattr(request.user, "channel", None)
    form = ChannelForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        channel = form.save(commit=False)
        channel.owner = request.user
        channel.save()
        messages.success(request, "تم حفظ القناة.")
        return redirect("dashboard")
    return render(request, "form_page.html", {"form": form, "page_title": "إنشاء قناتك أو تعديلها", "submit_label": "حفظ القناة", "form_kind": "channel"})
