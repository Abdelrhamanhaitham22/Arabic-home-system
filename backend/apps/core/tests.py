from types import SimpleNamespace
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import HomepageVideo, validate_video_size


class HomepageVideoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.active_video = HomepageVideo.objects.create(
            title_ar="درس التحية",
            title_ru="Урок приветствия",
            description_ar="تعلم التحية بالعربية.",
            description_ru="Учите приветствия на арабском.",
            video=SimpleUploadedFile("lesson.mp4", b"video"),
            order=2,
        )
        HomepageVideo.objects.create(
            title_ar="مخفي",
            title_ru="Скрыто",
            video=SimpleUploadedFile("hidden.webm", b"video"),
            order=1,
            is_active=False,
        )

    def test_public_endpoint_returns_only_active_videos_in_order(self):
        response = self.client.get("/api/core/videos/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.active_video.id)
        self.assertEqual(response.data[0]["title_ru"], "Урок приветствия")
        self.assertIn("/media/homepage/videos/lesson", response.data[0]["video_url"])

    def test_video_size_limit_rejects_large_uploads(self):
        large_file = SimpleNamespace(size=100 * 1024 * 1024 + 1)

        with self.assertRaises(ValidationError):
            validate_video_size(large_file)

    def test_uploaded_video_url_serves_the_video_file(self):
        response = self.client.get("/api/core/videos/")
        video_path = urlparse(response.data[0]["video_url"]).path

        media_response = self.client.get(video_path)

        self.assertEqual(media_response.status_code, 200)
        self.assertEqual(b"".join(media_response.streaming_content), b"video")

    def test_admin_can_save_uploaded_video(self):
        admin_user = self.create_admin_user()
        self.client.force_login(admin_user)
        form_data = {
            "title_ar": "فيديو جديد",
            "title_ru": "Новое видео",
            "description_ar": "وصف",
            "description_ru": "Описание",
            "video": SimpleUploadedFile("new-video.mp4", b"video"),
            "order": "0",
            "is_active": "on",
            "_save": "Save",
        }

        response = self.client.post(reverse("admin:core_homepagevideo_add"), form_data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(HomepageVideo.objects.filter(title_ar="فيديو جديد").exists())

    def create_admin_user(self):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
