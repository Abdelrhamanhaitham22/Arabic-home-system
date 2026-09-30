from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.exams.models import Level

from .models import TeacherProfile


class TeacherPortalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.level = Level.objects.create(name="Level 1", order=1)
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="teacher", password="secret")
        self.profile = TeacherProfile.objects.create(user=self.user, is_approved=True)
        self.profile.levels.add(self.level)

    def test_approved_teacher_can_login(self):
        response = self.client.post("/api/teachers/login/", {"username": "teacher", "password": "secret"})

        self.assertEqual(response.status_code, 200)

    def test_teacher_portal_no_longer_exposes_pdf_submissions(self):
        self.client.post("/api/teachers/login/", {"username": "teacher", "password": "secret"})

        response = self.client.get("/api/teachers/me/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("submissions", response.data)
        self.assertEqual(self.client.get("/api/teachers/submissions/1/file/").status_code, 404)
