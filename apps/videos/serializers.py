from rest_framework import serializers
from .models import Video

class VideoSerializer(serializers.ModelSerializer):
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    class Meta:
        model = Video
        fields = ("id", "title", "description", "thumbnail", "channel", "channel_name", "category", "category_name", "duration_seconds", "views_count", "published_at", "is_short")
        read_only_fields = fields
