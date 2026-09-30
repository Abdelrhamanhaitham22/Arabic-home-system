import datetime
from io import StringIO

from django.core.management import call_command
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

    def test_legacy_file_route_is_removed(self):
        self.assertEqual(
            self.client.get(f"/api/exams/{self.exam.id}/file/?student_code={self.student.student_code}").status_code,
            404,
        )


class SeedLevel6ExamCommandTests(TestCase):
    def test_seed_creates_canonical_draft_exam(self):
        output = StringIO()
        call_command("seed_level_6_exam", "--exam-date", "2026-10-01", stdout=output)
        exam = Exam.objects.get(name="Level 6 Final Exam")
        self.assertEqual(exam.level.name, "Level 6")
        self.assertEqual(exam.max_score, 80)
        self.assertEqual(exam.exam_date, datetime.date(2026, 10, 1))
        self.assertEqual(exam.status, "draft")
        self.assertEqual(list(exam.sections.values_list("name", "max_score")), [
            ("Reading", 15), ("Vocabulary", 15), ("Grammar", 15),
            ("Writing", 15), ("Listening", 10), ("Dictation", 10),
        ])
        self.assertIn("6 sections (80 points)", output.getvalue())

    def test_seed_is_idempotent_and_open_is_explicit(self):
        call_command("seed_level_6_exam", "--exam-date", "2026-10-01")
        call_command("seed_level_6_exam", "--exam-date", "2026-10-01", "--open")
        self.assertEqual(Exam.objects.count(), 1)
        self.assertEqual(ExamSection.objects.count(), 6)
        self.assertEqual(Exam.objects.get().status, "open")
