from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User
from apps.channels.models import Channel


class SignUpForm(UserCreationForm):
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("هذا البريد مستخدم بالفعل.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "email", "bio", "avatar", "preferred_language")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_email = self.instance.email if self.instance.pk else None

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise ValidationError("هذا البريد مستخدم في حساب آخر.")
        return email

    def clean_avatar(self):
        image = self.cleaned_data.get("avatar")
        if image and image.size > settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024:
            raise ValidationError(f"حجم الصورة يتجاوز الحد ({settings.MAX_IMAGE_UPLOAD_MB} م.ب).")
        return image

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.original_email is not None and user.email != self.original_email:
            user.email_verified = False
        if commit:
            user.save()
        return user


class ChannelForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ("name", "description", "avatar", "banner")

    def _clean_image_size(self, field):
        image = self.cleaned_data.get(field)
        if image and image.size > settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024:
            raise ValidationError(f"حجم الصورة يتجاوز الحد ({settings.MAX_IMAGE_UPLOAD_MB} م.ب).")
        return image

    def clean_avatar(self):
        return self._clean_image_size("avatar")

    def clean_banner(self):
        return self._clean_image_size("banner")
