import mimetypes
import posixpath
from pathlib import Path
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

PUBLIC_MEDIA_PREFIXES = ("avatars/", "channels/avatars/", "channels/banners/")


def route_manifest(request):
    path = Path(__file__).resolve().parent.parent / "static" / "manus-routes.json"
    try:
        handle = path.open("rb")
    except OSError as exc:
        raise Http404 from exc
    return FileResponse(handle, content_type="application/json; charset=utf-8")


def media_asset(request, path):
    if not path or ".." in path.split("/") or not path.startswith(PUBLIC_MEDIA_PREFIXES):
        raise Http404
    if not default_storage.exists(path):
        raise Http404
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    response = FileResponse(default_storage.open(path, "rb"), content_type=content_type)
    response["Cache-Control"] = "public, max-age=3600"
    return response


@require_GET
def video_thumbnail(request, pk):
    from apps.videos.models import Video
    video = Video.objects.select_related("channel").filter(pk=pk).first()
    owner = bool(video and request.user.is_authenticated and request.user.pk == video.channel.owner_id)
    if not video or not video.thumbnail or video.channel.is_suspended or (not owner and (video.status != Video.Status.READY or video.visibility == Video.Visibility.PRIVATE)):
        raise Http404
    response = FileResponse(video.thumbnail.storage.open(video.thumbnail.name, "rb"), content_type=mimetypes.guess_type(video.thumbnail.name)[0] or "image/jpeg")
    response["Cache-Control"] = "private, no-store"
    return response


def hls_asset(request, pk, asset):
    from apps.videos.models import Video
    video = Video.objects.select_related("channel").filter(pk=pk).first()
    if not video or not video.hls_manifest or video.status != Video.Status.READY or video.channel.is_suspended:
        raise Http404
    owner = request.user.is_authenticated and request.user.pk == video.channel.owner_id
    if video.visibility == Video.Visibility.PRIVATE and not owner:
        raise Http404
    if "\\" in asset or asset.startswith("/") or ".." in asset.split("/"):
        raise Http404
    asset = posixpath.normpath(asset)
    storage_name = f"videos/hls/{video.pk}/{asset}"
    if not default_storage.exists(storage_name):
        raise Http404
    if asset.endswith(".m3u8"):
        with default_storage.open(storage_name, "rb") as handle:
            lines = handle.read(2 * 1024 * 1024 + 1).decode("utf-8", errors="replace").splitlines()
        if sum(len(line) for line in lines) > 2 * 1024 * 1024:
            raise Http404
        parent = posixpath.dirname(asset)
        rewritten = []
        for line in lines:
            if line and not line.startswith("#"):
                child = posixpath.normpath(posixpath.join(parent, line.strip()))
                if child == ".." or child.startswith("../"):
                    raise Http404
                line = reverse("video_hls_asset", kwargs={"pk": pk, "asset": child})
            rewritten.append(line)
        response = HttpResponse("\n".join(rewritten) + "\n", content_type="application/vnd.apple.mpegurl")
    else:
        content_type = mimetypes.guess_type(asset)[0] or "application/octet-stream"
        response = FileResponse(default_storage.open(storage_name, "rb"), content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    return response


def not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)
