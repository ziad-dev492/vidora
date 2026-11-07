from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.channels.models import Channel
from apps.videos.models import Video

class PublicVideoApiTests(TestCase):
    def test_list_is_paginated_and_excludes_private_records(self):
        user = get_user_model().objects.create_user(username="apiowner", password="StrongPassword-12345")
        channel = Channel.objects.create(owner=user, name="API Channel", slug="api-channel")
        public = Video.objects.create(channel=channel, title="Public", video_file="videos/test.mp4", status="ready", visibility="public")
        Video.objects.create(channel=channel, title="Private", video_file="videos/private.mp4", status="ready", visibility="private")
        response = self.client.get(reverse("api-video-list"))
        self.assertEqual(response.status_code, 200)
        titles = [item["title"] for item in response.json()["results"]]
        self.assertIn(public.title, titles)
        self.assertNotIn("Private", titles)
