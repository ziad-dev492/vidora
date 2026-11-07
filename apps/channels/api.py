from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny
from .models import Channel

class ChannelSerializer(serializers.ModelSerializer):
    subscriber_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Channel
        fields = ("id", "name", "slug", "description", "avatar", "subscriber_count", "created_at")
        read_only_fields = fields

class ChannelViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChannelSerializer
    permission_classes = [AllowAny]
    search_fields = ["name", "description"]
    def get_queryset(self):
        from django.db.models import Count
        return Channel.objects.filter(is_suspended=False).annotate(annotated_subscriber_count=Count("subscriptions")).order_by("name")
