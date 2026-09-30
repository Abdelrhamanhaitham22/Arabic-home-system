from rest_framework import serializers

from .models import HomepageVideo


class HomepageVideoSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = HomepageVideo
        fields = (
            "id", "title_ar", "title_ru", "description_ar", "description_ru",
            "video_url", "order",
        )

    def get_video_url(self, obj):
        request = self.context.get("request")
        url = obj.video.url
        return request.build_absolute_uri(url) if request else url
