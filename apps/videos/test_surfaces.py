from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase
from django.urls import reverse
from apps.channels.models import Channel
from apps.notifications.models import Notification
from apps.playlists.models import Playlist, PlaylistVideo
from apps.videos.models import Category, Video

User = get_user_model()


class PrivacyAndSurfaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="surface-owner", email="surface@example.test", password="SafePassword-7890")
        cls.viewer = User.objects.create_user(username="surface-viewer", email="viewer@example.test", password="SafePassword-7890")
        cls.staff = User.objects.create_user(username="surface-staff", email="staff@example.test", password="SafePassword-7890", is_staff=True)
        cls.channel = Channel.objects.create(owner=cls.owner, name="Surface Channel", slug="surface-channel")
        cls.category = Category.objects.create(name="Surface Category", slug="surface-category")
        cls.video = Video.objects.create(channel=cls.channel, category=cls.category, title="Public surface video", video_file="videos/source/surface.mp4", visibility=Video.Visibility.PUBLIC, status=Video.Status.READY, duration_seconds=30)

    def test_private_thumbnail_uses_owner_checked_view(self):
        self.video.visibility = Video.Visibility.PRIVATE
        self.video.save(update_fields=("visibility",))
        self.video.thumbnail.save("private-surface.jpg", ContentFile(b"test image bytes"), save=True)
        self.addCleanup(default_storage.delete, self.video.thumbnail.name)
        url = reverse("video_thumbnail", args=[self.video.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get("/media/" + self.video.thumbnail.name).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_hls_playlist_rewrites_nested_asset_links_and_private_access(self):
        prefix = f"videos/hls/{self.video.pk}"
        assets = {
            f"{prefix}/master.m3u8": b"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=2520000,RESOLUTION=640x360\n360p/variant.m3u8\n",
            f"{prefix}/360p/variant.m3u8": b"#EXTM3U\n#EXTINF:5.0,\nsegment_00000.ts\n",
            f"{prefix}/360p/segment_00000.ts": b"segment bytes",
        }
        for name, data in assets.items():
            default_storage.save(name, ContentFile(data))
            self.addCleanup(default_storage.delete, name)
        self.video.hls_manifest.name = f"{prefix}/master.m3u8"
        self.video.save(update_fields=("hls_manifest",))
        response = self.client.get(reverse("video_hls_manifest", args=[self.video.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"/videos/{self.video.pk}/hls/360p/variant.m3u8", response.content.decode())
        self.video.visibility = Video.Visibility.PRIVATE
        self.video.save(update_fields=("visibility",))
        self.assertEqual(self.client.get(reverse("video_hls_manifest", args=[self.video.pk])).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("video_hls_manifest", args=[self.video.pk])).status_code, 200)

    def test_unlisted_content_is_not_in_public_home_but_direct_link_is_supported(self):
        self.video.visibility = Video.Visibility.UNLISTED
        self.video.save(update_fields=("visibility",))
        self.assertNotContains(self.client.get(reverse("home")), self.video.title)
        self.assertEqual(self.client.get(reverse("video_detail", args=[self.video.pk])).status_code, 200)

    def test_private_playlist_management_requires_owner(self):
        playlist = Playlist.objects.create(owner=self.owner, title="My private list", is_public=False)
        detail = reverse("playlist_detail", args=[playlist.pk])
        self.assertEqual(self.client.get(detail).status_code, 403)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(detail).status_code, 200)
        response = self.client.post(reverse("playlist_add", args=[playlist.pk]), {"video_id": self.video.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PlaylistVideo.objects.filter(playlist=playlist, video=self.video).count(), 1)
        self.client.post(reverse("playlist_manage", args=[playlist.pk]), {"action": "update", "title": "Updated list", "description": "Personal", "is_public": "on"})
        playlist.refresh_from_db()
        self.assertEqual(playlist.title, "Updated list")
        self.assertTrue(playlist.is_public)

    def test_owner_and_staff_dashboards_render_with_server_side_permissions(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)
        self.client.force_login(self.viewer)
        self.assertNotEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)

    def test_new_like_notifies_channel_owner_and_unlike_does_not_repeat(self):
        self.client.force_login(self.viewer)
        response = self.client.post(reverse("like", args=[self.video.pk]))
        self.assertEqual(response.status_code, 302)
        notification = Notification.objects.get(recipient=self.owner, kind="like")
        self.client.post(reverse("like", args=[self.video.pk]))
        self.assertEqual(Notification.objects.filter(recipient=self.owner, kind="like").count(), 1)
        self.assertIn(str(self.video.pk), notification.target_url)
