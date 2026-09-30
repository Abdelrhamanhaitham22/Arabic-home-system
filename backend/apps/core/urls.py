from django.urls import path

from .views import homepage_videos


urlpatterns = [
    path("videos/", homepage_videos, name="homepage-videos"),
]
