import datetime

from django.test import TestCase
from rest_framework.test import APIClient

from apps.students.models import Student

from .models import Exam, ExamSection, Level


class AvailableExamApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.level = Level.objects.create(name="Level 6", order=6)
        self.exam = Exam.objects.create(
            level=self.level,
            name="Level 6 Online Exam",
            max_score=100,
            exam_date=datetime.date(2026, 9, 30),
            status="open",
        )
        ExamSection.objects.create(exam=self.exam, name="Reading", max_score=100, order=1)
        self.student = Student.objects.create(
            full_name="Ahmed Mohamed",
            phone_number="+20101234567",
            address="Alexandria, Egypt",
            passport_number="P1234567",
            level=self.level,
        )

    def test_open_exam_is_listed_without_legacy_file_url(self):
        response = self.client.get(f"/api/exams/?student_code={self.student.student_code}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["name"], "Level 6 Online Exam")
        self.assertNotIn("exam_file_url", response.data[0])

    def test_legacy_file_and_submission_routes_are_removed(self):
        self.assertEqual(
            self.client.get(f"/api/exams/{self.exam.id}/file/?student_code={self.student.student_code}").status_code,
            404,
        )
        self.assertEqual(self.client.post("/api/exams/submissions/").status_code, 404)
