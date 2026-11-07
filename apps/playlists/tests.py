from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from apps.channels.models import Channel
from apps.videos.models import Video
from apps.playlists.models import Playlist, PlaylistVideo, WatchLater

User = get_user_model()

class PlaylistConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="listuser", password="SafePassword-98765")
        channel = Channel.objects.create(owner=self.user, name="List channel", slug="list-channel")
        self.video = Video.objects.create(channel=channel, title="List video", video_file="videos/source/list.mp4", status="ready", visibility="public")
        self.playlist = Playlist.objects.create(owner=self.user, title="Saved")
    def test_duplicate_playlist_video_is_rejected(self):
        PlaylistVideo.objects.create(playlist=self.playlist, video=self.video)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlaylistVideo.objects.create(playlist=self.playlist, video=self.video)
    def test_duplicate_watch_later_is_rejected(self):
        WatchLater.objects.create(user=self.user, video=self.video)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WatchLater.objects.create(user=self.user, video=self.video)
