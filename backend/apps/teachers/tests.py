from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.exams.models import Level
from apps.students.models import Student

from .models import TeacherAssessment, TeacherAssessmentConfig, TeacherProfile


class TeacherPortalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.level = Level.objects.create(name="Level 1", order=1)
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="teacher", password="secret")
        self.profile = TeacherProfile.objects.create(user=self.user, is_approved=True)
        self.profile.levels.add(self.level)
        self.student = Student.objects.create(
            full_name="Student One",
            phone_number="123",
            address="Address",
            passport_number="PASS-1",
            level=self.level,
        )

    def test_approved_teacher_can_login(self):
        response = self.client.post("/api/teachers/login/", {"username": "teacher", "password": "secret"})

        self.assertEqual(response.status_code, 200)

    def test_teacher_portal_no_longer_exposes_pdf_submissions(self):
        self.client.post("/api/teachers/login/", {"username": "teacher", "password": "secret"})

        response = self.client.get("/api/teachers/me/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("submissions", response.data)
        self.assertEqual(self.client.get("/api/teachers/submissions/1/file/").status_code, 404)

    def test_teacher_can_save_scores_with_configured_limits(self):
        TeacherAssessmentConfig.objects.create(
            level=self.level, written_max=75, activity_dictation_max=50, oral_max=75
        )
        self.client.post("/api/teachers/login/", {"username": "teacher", "password": "secret"})

        response = self.client.put(
            f"/api/teachers/assessments/{self.student.student_code}/",
            {"written_score": "75", "activity_dictation_score": "50", "oral_score": "75"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_score"], 125.0)
        self.assertEqual(TeacherAssessment.objects.count(), 1)

    def test_teacher_cannot_exceed_configured_limit(self):
        TeacherAssessmentConfig.objects.create(level=self.level, written_max=75)
        self.client.post("/api/teachers/login/", {"username": "teacher", "password": "secret"})

        response = self.client.put(
            f"/api/teachers/assessments/{self.student.student_code}/",
            {"written_score": "76"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
