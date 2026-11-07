from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import Video


class VideoUploadForm(forms.ModelForm):
    tags_text = forms.CharField(required=False, max_length=500, label="الوسوم", help_text="افصل الوسوم بفاصلة")

    class Meta:
        model = Video
        fields = ("title", "description", "category", "video_file", "thumbnail", "visibility", "comments_enabled")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def clean_video_file(self):
        upload = self.cleaned_data.get("video_file")
        if not upload:
            return upload
        if upload.size > settings.MAX_VIDEO_UPLOAD_MB * 1024 * 1024:
            raise ValidationError(f"حجم الفيديو يتجاوز الحد ({settings.MAX_VIDEO_UPLOAD_MB} م.ب).")
        head = upload.read(16)
        upload.seek(0)
        valid = (head[4:8] == b"ftyp" or head.startswith(b"\x1aE\xdf\xa3") or
                 head.startswith(b"RIFF") and head[8:12] == b"AVI " or
                 head.startswith(b"\x00\x00\x01\xba") or head.startswith(b"\x00\x00\x01\xb3") or
                 bool(head) and head[0] == 0x47)
        if not valid:
            raise ValidationError("صيغة الملف لا تبدو فيديو صالحًا. الصيغ الشائعة: MP4 أو WebM أو AVI أو MPEG.")
        return upload

    def clean_thumbnail(self):
        image = self.cleaned_data.get("thumbnail")
        if image:
            if image.size > settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024:
                raise ValidationError(f"حجم الصورة يتجاوز الحد ({settings.MAX_IMAGE_UPLOAD_MB} م.ب).")
            try:
                from PIL import Image
                image.seek(0)
                with Image.open(image) as opened:
                    opened.verify()
                image.seek(0)
            except Exception as exc:
                raise ValidationError("الصورة المصغرة غير صالحة أو غير مدعومة.") from exc
        return image
