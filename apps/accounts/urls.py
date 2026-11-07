from django.contrib.auth import views as auth_views
from django.urls import path
from apps.core.rate_limit import rate_limit
from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", rate_limit(10, 300, "login")(auth_views.LoginView.as_view(template_name="form_page.html", extra_context={"page_title": "تسجيل الدخول", "submit_label": "دخول", "form_kind": "login"})), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("settings/", views.profile_settings, name="settings"),
    path("channel/", views.create_or_edit_channel, name="channel_setup"),
    path("email/verify/<str:token>/", views.verify_email, name="email_verify"),
    path("email/resend/", views.resend_verification, name="email_resend"),
    path("password-reset/", rate_limit(5, 3600, "password_reset")(auth_views.PasswordResetView.as_view(template_name="registration/password_reset_form.html", email_template_name="registration/password_reset_email.html", success_url="/accounts/password-reset/done/")), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="registration/password_reset_confirm.html", success_url="/accounts/reset/done/"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
]
