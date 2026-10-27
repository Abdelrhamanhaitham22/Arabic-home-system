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

    def test_signup_requires_admin_approval_and_assigned_level(self):
        response = self.client.post(
            "/api/teachers/signup/",
            {"username": "new teacher", "password": "A-strong-password-123"},
        )
        self.assertEqual(response.status_code, 201)
        profile = TeacherProfile.objects.get(user__username="new teacher")
        self.assertFalse(profile.is_approved)
        self.assertEqual(self.client.post(
            "/api/teachers/login/",
            {"username": "new teacher", "password": "A-strong-password-123"},
        ).status_code, 403)

        profile.is_approved = True
        profile.save(update_fields=["is_approved"])
        self.assertEqual(self.client.post(
            "/api/teachers/login/",
            {"username": "new teacher", "password": "A-strong-password-123"},
        ).status_code, 403)
        profile.levels.add(self.level)
        self.assertEqual(self.client.post(
            "/api/teachers/login/",
            {"username": "new teacher", "password": "A-strong-password-123"},
        ).status_code, 200)
        portal = self.client.get("/api/teachers/me/")
        self.assertEqual([student["student_code"] for student in portal.data["students"]], [self.student.student_code])

    def test_revoked_approval_blocks_existing_session(self):
        self.client.post("/api/teachers/login/", {"username": "teacher", "password": "secret"})
        self.profile.is_approved = False
        self.profile.save(update_fields=["is_approved"])

        self.assertEqual(self.client.get("/api/teachers/me/").status_code, 403)
        self.assertEqual(self.client.put(
            f"/api/teachers/assessments/{self.student.student_code}/",
            {"activity_dictation_score": "10", "oral_score": "10"},
        ).status_code, 403)

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

    def test_teacher_cannot_exceed_configured_teacher_section_limit(self):
        TeacherAssessmentConfig.objects.create(level=self.level, written_max=75)
        self.client.post("/api/teachers/login/", {"username": "teacher", "password": "secret"})

        response = self.client.put(
            f"/api/teachers/assessments/{self.student.student_code}/",
            {"activity_dictation_score": "51"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_teacher_can_delete_assessment(self):
        TeacherAssessmentConfig.objects.create(level=self.level)
        self.client.post("/api/teachers/login/", {"username": "teacher", "password": "secret"})
        self.client.put(
            f"/api/teachers/assessments/{self.student.student_code}/",
            {"activity_dictation_score": "20", "oral_score": "20"},
            format="json",
        )

        response = self.client.delete(f"/api/teachers/assessments/{self.student.student_code}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(TeacherAssessment.objects.exists())
