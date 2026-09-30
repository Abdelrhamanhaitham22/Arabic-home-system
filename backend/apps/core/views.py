from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import HomepageVideo
from .serializers import HomepageVideoSerializer


def health_check(request):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


@api_view(["GET"])
def homepage_videos(request):
    videos = HomepageVideo.objects.filter(is_active=True)
    return Response(HomepageVideoSerializer(videos, many=True, context={"request": request}).data)
