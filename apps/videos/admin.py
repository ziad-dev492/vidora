from django.contrib import admin
from apps.channels.models import Channel, Subscription
from apps.videos.models import Category, Tag, Video, VideoProcessingJob, VideoRendition
from apps.interactions.models import Comment, VideoLike, VideoView
from apps.playlists.models import Playlist, PlaylistVideo, WatchHistory, WatchLater
from apps.notifications.models import Notification, Report, AuditLog

admin.site.register((Channel, Subscription, Category, Tag, Video, VideoProcessingJob, VideoRendition,
                     Comment, VideoLike, VideoView, Playlist, PlaylistVideo, WatchHistory, WatchLater,
                     Notification, Report, AuditLog))
