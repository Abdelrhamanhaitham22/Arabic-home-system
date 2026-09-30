import datetime

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
            address="Alexandria",
            passport_number="P1234567",
        )
        self.exam = Exam.objects.create(
            name="Online Placement Exam",
            max_score=100,
            exam_date=datetime.date(2026, 9, 30),
        )

    def test_lookup_returns_published_result(self):
        Result.objects.create(student=self.student, exam=self.exam, score=80, published=True)

        response = self.client.get(f"/api/results/{self.student.student_code}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["percentage"], 80.0)
        self.assertNotIn("passport_number", response.data)

    def test_unpublished_result_is_hidden(self):
        Result.objects.create(student=self.student, exam=self.exam, score=80)

        response = self.client.get(f"/api/results/{self.student.student_code}/")

        self.assertEqual(response.data["results"], [])
