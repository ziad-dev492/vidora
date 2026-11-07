import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from celery import shared_task
from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from .models import Video, VideoProcessingJob, VideoRendition
from apps.notifications.tasks import notify_subscribers


def _run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=3600)


def _clear_storage_prefix(prefix):
    try:
        directories, files = default_storage.listdir(prefix)
    except (FileNotFoundError, NotImplementedError):
        return
    for name in files:
        default_storage.delete(f"{prefix}/{name}")
    for name in directories:
        _clear_storage_prefix(f"{prefix}/{name}")


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def process_video(self, video_id):
    video = Video.objects.select_related("channel").get(pk=video_id)
    job = VideoProcessingJob.objects.filter(video=video).order_by("-created_at").first()
    if job is None:
        job = VideoProcessingJob.objects.create(video=video)
    job.state, job.started_at, job.attempts, job.error_message = VideoProcessingJob.State.RUNNING, timezone.now(), job.attempts + 1, ""
    job.save(update_fields=("state", "started_at", "attempts", "error_message"))
    video.status = Video.Status.PROCESSING
    video.save(update_fields=("status",))
    try:
        with tempfile.TemporaryDirectory(prefix="vidora-ffmpeg-") as tmp:
            source = Path(tmp) / "source.bin"
            with video.video_file.open("rb") as incoming, source.open("wb") as outgoing:
                shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
            probe = _run([os.getenv("FFPROBE_BINARY", "ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)])
            info = json.loads(probe.stdout)
            stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
            if not stream:
                raise ValueError("لم يعثر FFprobe على مسار فيديو داخل الملف.")
            duration = max(0, int(float(info.get("format", {}).get("duration", 0))))
            width, height = int(stream.get("width", 0)), int(stream.get("height", 0))
            thumb = Path(tmp) / "thumbnail.jpg"
            _run([os.getenv("FFMPEG_BINARY", "ffmpeg"), "-y", "-ss", str(min(2, max(0, duration // 3))), "-i", str(source), "-frames:v", "1", "-vf", "scale='min(640,iw)':-2", str(thumb)])
            with thumb.open("rb") as image:
                if not video.thumbnail:
                    name = default_storage.save(f"videos/thumbnails/{video.pk}.jpg", File(image))
                    video.thumbnail.name = name
            best_output = None
            rendition_outputs = []
            for quality in (360, 480, 720, 1080):
                if not height or height < quality:
                    continue
                output = Path(tmp) / f"{quality}p.mp4"
                _run([os.getenv("FFMPEG_BINARY", "ffmpeg"), "-y", "-i", str(source), "-vf", f"scale=-2:min(ih\\,{quality})", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-c:a", "aac", "-movflags", "+faststart", str(output)])
                if output.exists() and output.stat().st_size:
                    best_output = output
                    with output.open("rb") as encoded:
                        rendition, _ = VideoRendition.objects.get_or_create(video=video, quality=quality)
                        if rendition.file.name:
                            default_storage.delete(rendition.file.name)
                        name = default_storage.save(f"videos/renditions/{video.pk}/{quality}p.mp4", File(encoded))
                        rendition.file.name = name
                        rendition.save(update_fields=("file",))
                        rendition_outputs.append((quality, output))
            if settings.ENABLE_HLS:
                hls_dir = Path(tmp) / "hls"
                hls_dir.mkdir()
                sources = rendition_outputs or [(height or 360, source)]
                master_lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
                for quality, hls_source in sources:
                    variant_dir = hls_dir / f"{quality}p"
                    variant_dir.mkdir()
                    playlist = variant_dir / "variant.m3u8"
                    _run([os.getenv("FFMPEG_BINARY", "ffmpeg"), "-y", "-i", str(hls_source), "-c", "copy", "-hls_time", "6", "-hls_playlist_type", "vod", "-hls_segment_filename", str(variant_dir / "segment_%05d.ts"), str(playlist)])
                    rendition_width = max(2, (width * quality // max(height, 1)) // 2 * 2)
                    master_lines.extend([f"#EXT-X-STREAM-INF:BANDWIDTH={quality * 7000},RESOLUTION={rendition_width}x{quality}", f"{quality}p/variant.m3u8"])
                _clear_storage_prefix(f"videos/hls/{video.pk}")
                for asset in hls_dir.rglob("*"):
                    if not asset.is_file():
                        continue
                    with asset.open("rb") as content:
                        relative_path = asset.relative_to(hls_dir).as_posix()
                        destination = f"videos/hls/{video.pk}/{relative_path}"
                        if default_storage.exists(destination):
                            default_storage.delete(destination)
                        default_storage.save(destination, File(content))
                master = "\n".join(master_lines) + "\n"
                master_path = f"videos/hls/{video.pk}/master.m3u8"
                if default_storage.exists(master_path):
                    default_storage.delete(master_path)
                video.hls_manifest.name = default_storage.save(master_path, ContentFile(master.encode()))
            video.duration_seconds, video.width, video.height = duration, width, height
            video.is_short = bool(duration <= 60 and height > width)
            video.status = Video.Status.READY
            video.published_at = video.published_at or timezone.now()
            video.save(update_fields=("thumbnail", "hls_manifest", "duration_seconds", "width", "height", "is_short", "status", "published_at"))
        job.state, job.finished_at = VideoProcessingJob.State.SUCCEEDED, timezone.now()
        job.save(update_fields=("state", "finished_at"))
        try:
            notify_subscribers.delay(video.pk)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Video %s is ready, but subscriber notification could not be queued", video.pk)
        return {"video_id": video_id, "state": job.state}
    except Exception as exc:
        job.state, job.finished_at = VideoProcessingJob.State.FAILED, timezone.now()
        job.error_message = str(exc)[:2000]
        job.save(update_fields=("state", "finished_at", "error_message"))
        video.status = Video.Status.FAILED
        video.save(update_fields=("status",))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise
