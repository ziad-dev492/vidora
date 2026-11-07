import json
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from urllib.parse import urlsplit
from apps.channels.models import Channel, Subscription
from apps.interactions.models import VideoLike
from apps.videos.models import Category, Video

User = get_user_model()


class VidoraCoreTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="creator", email="creator@example.test", password="StrongPass-4242")
        cls.viewer = User.objects.create_user(username="viewer", email="viewer@example.test", password="StrongPass-4242")
        cls.channel = Channel.objects.create(owner=cls.owner, name="Creator Channel", slug="creator-channel")
        cls.category = Category.objects.create(name="Technology", slug="technology")
        cls.video = Video.objects.create(channel=cls.channel, category=cls.category, title="A real test title", video_file="videos/source/test.mp4", visibility="public", status="ready", duration_seconds=80)

    def setUp(self):
        cache.clear()

    def test_home_renders_and_uses_database(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.video.title)

    def test_signup_creates_user_with_hashed_password(self):
        response = self.client.post(reverse("signup"), {"username": "newviewer", "email": "new@example.test", "password1": "SafePassword-98765", "password2": "SafePassword-98765"})
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newviewer")
        self.assertNotEqual(user.password, "SafePassword-98765")
        self.assertTrue(user.check_password("SafePassword-98765"))

    def test_email_verification_link_confirms_address(self):
        self.client.post(reverse("signup"), {"username": "mailviewer", "email": "mail@example.test", "password1": "SafePassword-98765", "password2": "SafePassword-98765"})
        user = User.objects.get(username="mailviewer")
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        path = urlsplit(mail.outbox[0].body.splitlines()[-1]).path
        response = self.client.get(path)
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_signup_rate_limit_returns_429(self):
        statuses = [self.client.post(reverse("signup"), {}).status_code for _ in range(6)]
        self.assertEqual(statuses[:5], [200] * 5)
        self.assertEqual(statuses[5], 429)

    def test_login_logout(self):
        self.assertTrue(self.client.login(username="viewer", password="StrongPass-4242"))
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)

    def test_private_video_is_not_accessible_to_other_user(self):
        self.video.visibility = "private"
        self.video.save(update_fields=("visibility",))
        self.assertEqual(self.client.get(reverse("video_detail", args=[self.video.pk])).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("video_detail", args=[self.video.pk])).status_code, 200)

    def test_like_requires_login_and_toggles_without_duplicates(self):
        url = reverse("like", args=[self.video.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.viewer)
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(VideoLike.objects.filter(user=self.viewer, video=self.video).count(), 0)
        self.client.post(url)
        self.assertEqual(VideoLike.objects.filter(user=self.viewer, video=self.video).count(), 1)

    def test_subscription_has_database_uniqueness(self):
        Subscription.objects.create(subscriber=self.viewer, channel=self.channel)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Subscription.objects.create(subscriber=self.viewer, channel=self.channel)

    def test_search_reads_database(self):
        response = self.client.get(reverse("search"), {"q": "real test"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.video.title)

    def test_upload_rejects_non_video_signature(self):
        self.client.force_login(self.owner)
        bad = SimpleUploadedFile("bad.mp4", b"this is not a movie file", content_type="video/mp4")
        response = self.client.post(reverse("upload_video"), {"title": "Bad upload", "video_file": bad, "category": self.category.pk, "visibility": "public"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "صيغة الملف لا تبدو فيديو صالحًا")


class StreamingPrivacyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="streamowner", password="SafePassword-98765")
        cls.channel = Channel.objects.create(owner=cls.owner, name="Stream Channel", slug="stream-channel")
        cls.video = Video.objects.create(channel=cls.channel, title="Streamable", video_file="videos/source/private.mp4", status="ready", visibility="public")

    def test_range_stream_and_view_deduplication(self):
        self.video.video_file.save("range-test.mp4", ContentFile(b"0123456789"), save=True)
        self.addCleanup(default_storage.delete, self.video.video_file.name)
        url = reverse("stream_video", args=[self.video.pk])
        response = self.client.get(url, HTTP_RANGE="bytes=2-5")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(b"".join(response.streaming_content), b"2345")
        response.close()
        second_response = self.client.get(url, HTTP_RANGE="bytes=0-1")
        self.assertEqual(b"".join(second_response.streaming_content), b"01")
        second_response.close()
        self.video.refresh_from_db()
        self.assertEqual(self.video.views_count, 1)

    def test_original_media_path_is_never_a_public_static_file(self):
        response = self.client.get("/media/videos/source/private.mp4")
        self.assertEqual(response.status_code, 404)

    def test_private_thumbnail_is_only_available_on_authorized_route(self):
        self.video.visibility = Video.Visibility.PRIVATE
        self.video.save(update_fields=("visibility",))
        self.video.thumbnail.save("private-thumb.jpg", ContentFile(b"test image bytes"), save=True)
        self.addCleanup(default_storage.delete, self.video.thumbnail.name)
        protected_url = reverse("video_thumbnail", args=[self.video.pk])
        self.assertEqual(self.client.get(protected_url).status_code, 404)
        direct = self.client.get("/media/" + self.video.thumbnail.name)
        self.assertEqual(direct.status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(protected_url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_route_manifest_is_served_from_site_root(self):
        response = self.client.get(reverse("route_manifest"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"].split(";")[0], "application/json")
        payload = json.loads(b"".join(response.streaming_content).decode("utf-8"))
        self.assertIn("/videos/:pk/", [item["path"] for item in payload["routes"]])
