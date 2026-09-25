import datetime

from django.contrib.auth import get_user_model
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from apps.exams.models import Exam, ExamSection, Level
from apps.results.models import ExamSubmission, Result

from .models import TeacherProfile


class TeacherPortalTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.level_one = Level.objects.create(name="Level 1", order=1)
        self.level_two = Level.objects.create(name="Level 2", order=2)
        self.exam_one = Exam.objects.create(
            name="Level One Exam",
            level=self.level_one,
            max_score=15,
            exam_date=datetime.date(2026, 9, 14),
        )
        self.exam_two = Exam.objects.create(
            name="Level Two Exam",
            level=self.level_two,
            max_score=15,
            exam_date=datetime.date(2026, 9, 14),
        )
        self.section_one = ExamSection.objects.create(
            exam=self.exam_one, name="Reading", max_score=15, order=1
        )
        self.student_one = self.make_student("Student One")
        self.student_two = self.make_student("Student Two")
        self.student_one.level = self.level_one
        self.student_one.save(update_fields=("level",))
        self.student_two.level = self.level_two
        self.student_two.save(update_fields=("level",))
        self.submission_one = ExamSubmission.objects.create(
            student=self.student_one,
            exam=self.exam_one,
            answer_file=SimpleUploadedFile("answers.pdf", b"%PDF-1.4"),
        )
        self.submission_two = ExamSubmission.objects.create(
            student=self.student_two,
            exam=self.exam_two,
            answer_file=SimpleUploadedFile("answers-two.pdf", b"%PDF-1.4"),
        )
        user_model = get_user_model()
        self.teacher_user = user_model.objects.create_user(username="teacher", password="secret")
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, is_approved=True)
        self.teacher.levels.add(self.level_one)
        self.admin_user = user_model.objects.create_user(username="admin", password="secret")

    @staticmethod
    def make_student(name):
        from apps.students.models import Student

        return Student.objects.create(
            full_name=name,
            phone_number="+20100000000",
            address="Alexandria",
            passport_number=f"P-{name}",
        )

    def login(self):
        response = self.client.post("/api/teachers/login/", {"username": "teacher", "password": "secret"})
        self.assertEqual(response.status_code, 200)

    def test_teacher_login_requires_teacher_profile(self):
        response = self.client.post("/api/teachers/login/", {"username": "admin", "password": "secret"})

        self.assertEqual(response.status_code, 401)

    def test_teacher_signup_creates_pending_profile(self):
        response = self.client.post(
            "/api/teachers/signup/",
            {"username": "newteacher", "password": "StrongPassword123!"},
        )

        self.assertEqual(response.status_code, 201)
        profile = TeacherProfile.objects.get(user__username="newteacher")
        self.assertFalse(profile.is_approved)
        login_response = self.client.post(
            "/api/teachers/login/",
            {"username": "newteacher", "password": "StrongPassword123!"},
        )
        self.assertEqual(login_response.status_code, 403)

    def test_approved_teacher_can_login(self):
        response = self.client.post(
            "/api/teachers/login/",
            {"username": "teacher", "password": "secret"},
        )

        self.assertEqual(response.status_code, 200)

    def test_approved_teacher_login_is_case_insensitive_for_username(self):
        response = self.client.post(
            "/api/teachers/login/",
            {"username": "TEACHER", "password": "secret"},
        )

        self.assertEqual(response.status_code, 200)

    def test_teacher_login_normalizes_username_spacing(self):
        response = self.client.post(
            "/api/teachers/login/",
            {"username": "  teacher  ", "password": "secret"},
        )

        self.assertEqual(response.status_code, 200)

    def test_teacher_csrf_endpoint_returns_token(self):
        response = self.client.get("/api/teachers/csrf/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["csrf_token"]), 64)

    def test_teacher_users_are_not_in_generic_admin_user_table(self):
        user_admin = admin.site._registry[get_user_model()]

        request = RequestFactory().get("/admin/auth/user/")
        usernames = set(user_admin.get_queryset(request).values_list("username", flat=True))

        self.assertNotIn(self.teacher_user.username, usernames)

    def test_teacher_submissions_are_limited_to_assigned_levels(self):
        self.login()

        response = self.client.get("/api/teachers/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["submissions"]], [self.submission_one.id])
        self.assertEqual([item["student_code"] for item in response.data["students"]], [self.student_one.student_code])

    def test_teacher_can_filter_submissions_and_students_by_assigned_level(self):
        self.teacher.levels.add(self.level_two)
        self.login()

        response = self.client.get(f"/api/teachers/me/?level_id={self.level_two.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["submissions"]], [self.submission_two.id])
        self.assertEqual([item["student_code"] for item in response.data["students"]], [self.student_two.student_code])

    def test_teacher_cannot_filter_by_unassigned_level(self):
        self.login()

        response = self.client.get(f"/api/teachers/me/?level_id={self.level_two.id}")

        self.assertEqual(response.status_code, 400)

    def test_teacher_cannot_open_unassigned_answer_file(self):
        self.login()

        response = self.client.get(f"/api/teachers/submissions/{self.submission_two.id}/file/")

        self.assertEqual(response.status_code, 404)

    def test_teacher_can_save_and_publish_assigned_submission(self):
        self.login()

        response = self.client.put(
            f"/api/teachers/submissions/{self.submission_one.id}/grade/",
            {
                "sections": [
                    {"section_id": self.section_one.id, "score": 13, "teacher_comment": "Good work."}
                ],
                "teacher_notes": "Strong result.",
                "publish": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        result = Result.objects.get(submission=self.submission_one)
        self.assertTrue(result.published)
        self.assertEqual(result.score, 13)
        self.assertEqual(result.teacher_notes, "Strong result.")

    def test_teacher_cannot_publish_incomplete_grade(self):
        self.login()

        ExamSection.objects.create(exam=self.exam_one, name="Writing", max_score=10, order=2)
        response = self.client.put(
            f"/api/teachers/submissions/{self.submission_one.id}/grade/",
            {
                "sections": [{"section_id": self.section_one.id, "score": 13}],
                "publish": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Result.objects.filter(submission=self.submission_one).exists())

    def test_invalid_grade_does_not_persist_previous_section_scores(self):
        second_section = ExamSection.objects.create(
            exam=self.exam_one, name="Writing", max_score=10, order=2
        )
        self.login()

        response = self.client.put(
            f"/api/teachers/submissions/{self.submission_one.id}/grade/",
            {
                "sections": [
                    {"section_id": self.section_one.id, "score": 13},
                    {"section_id": second_section.id, "score": 11},
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Result.objects.filter(submission=self.submission_one).exists())

    def test_failed_publish_does_not_persist_draft_changes(self):
        ExamSection.objects.create(
            exam=self.exam_one, name="Writing", max_score=10, order=2
        )
        self.login()

        response = self.client.put(
            f"/api/teachers/submissions/{self.submission_one.id}/grade/",
            {
                "sections": [{"section_id": self.section_one.id, "score": 13}],
                "teacher_notes": "Should roll back",
                "publish": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Result.objects.filter(submission=self.submission_one).exists())

    def test_teacher_cannot_exceed_section_maximum(self):
        self.login()

        response = self.client.put(
            f"/api/teachers/submissions/{self.submission_one.id}/grade/",
            {"sections": [{"section_id": self.section_one.id, "score": 16}]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
