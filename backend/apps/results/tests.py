import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.exams.models import Exam
from apps.students.models import Student

from .models import Result


class ResultLookupApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = Student.objects.create(
            full_name="Ahmed Mohamed",
            phone_number="+20101234567",
            address="Alexandria, Egypt",
            passport_number="P1234567",
        )
        self.exam = Exam.objects.create(
            name="Arabic Placement Exam",
            max_score=200,
            exam_date=datetime.date(2026, 9, 7),
        )

    def test_lookup_with_result_returns_percentage_without_private_data(self):
        Result.objects.create(student=self.student, exam=self.exam, score=120)

        response = self.client.get(f"/api/results/{self.student.student_code}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["percentage"], 60.0)
        self.assertNotIn("passport_number", response.data)

    def test_lookup_without_result_explains_result_is_pending(self):
        response = self.client.get(f"/api/results/{self.student.student_code}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])
        self.assertIn("message", response.data)

    def test_lookup_with_unknown_code_returns_not_found_error(self):
        response = self.client.get("/api/results/ST209999999/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "student_not_found")

    def test_result_score_above_exam_limit_is_rejected(self):
        result = Result(student=self.student, exam=self.exam, score=201)

        with self.assertRaises(ValidationError):
            result.full_clean()
