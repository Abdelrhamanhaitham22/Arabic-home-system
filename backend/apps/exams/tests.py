import datetime
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.students.models import Student

from .models import Exam, ExamSection, Level, Question, QuestionChoice


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
            time_limit_minutes=45,
        )
        ExamSection.objects.create(exam=self.exam, name="Reading", max_score=100, order=1)
        section = self.exam.sections.get()
        multiple_choice = Question.objects.create(
            section=section,
            prompt="Choose the greeting.",
            question_type="multiple_choice",
            points=2,
            order=1,
        )
        QuestionChoice.objects.create(question=multiple_choice, text="مرحبا", order=1, is_correct=True)
        QuestionChoice.objects.create(question=multiple_choice, text="وداعا", order=2)
        Question.objects.create(
            section=section,
            prompt="Write a sentence.",
            question_type="written",
            points=5,
            order=2,
        )
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

    def test_exam_detail_returns_questions_without_correct_answers(self):
        response = self.client.get(
            f"/api/exams/{self.exam.id}/?student_code={self.student.student_code}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["time_limit_minutes"], 45)
        questions = response.data["sections"][0]["questions"]
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0]["question_type"], "multiple_choice")
        self.assertEqual(questions[0]["choices"][0]["text"], "مرحبا")
        self.assertNotIn("is_correct", questions[0]["choices"][0])

    def test_exam_detail_rejects_student_from_another_level(self):
        other_level = Level.objects.create(name="Level 7", order=7)
        other_student = Student.objects.create(
            full_name="Other Student",
            phone_number="+20101234568",
            address="Cairo, Egypt",
            passport_number="P1234568",
            level=other_level,
        )

        response = self.client.get(
            f"/api/exams/{self.exam.id}/?student_code={other_student.student_code}"
        )

        self.assertEqual(response.status_code, 404)


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
