import datetime
from io import StringIO

from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.students.models import Student

from .models import Exam, ExamSection, Level


class SeedLevel6ExamCommandTests(TestCase):
    def test_command_creates_level_exam_and_scoring_sections(self):
        output = StringIO()

        call_command("seed_level_6_exam", "--exam-date", "2026-09-14", stdout=output)

        level = Level.objects.get(name="Level 6")
        exam = Exam.objects.get(name="Level 6 Final Exam")
        sections = list(ExamSection.objects.filter(exam=exam))

        self.assertEqual(level.order, 6)
        self.assertEqual(exam.level, level)
        self.assertEqual(exam.exam_date, datetime.date(2026, 9, 14))
        self.assertEqual(exam.max_score, 80)
        self.assertEqual(
            [(section.name, section.max_score) for section in sections],
            [
                ("Reading", 15),
                ("Vocabulary", 15),
                ("Grammar", 15),
                ("Writing", 15),
                ("Listening", 10),
                ("Dictation", 10),
            ],
        )

    def test_command_is_idempotent(self):
        call_command("seed_level_6_exam", "--exam-date", "2026-09-14")
        call_command("seed_level_6_exam", "--exam-date", "2026-09-15")

        self.assertEqual(Level.objects.filter(name="Level 6").count(), 1)
        self.assertEqual(Exam.objects.filter(name="Level 6 Final Exam").count(), 1)
        self.assertEqual(ExamSection.objects.count(), 6)


class ExamSubmissionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.level = Level.objects.create(name="Level 6", order=6)
        self.exam = Exam.objects.create(
            level=self.level,
            name="Level 6 Final Exam",
            max_score=80,
            exam_date=datetime.date(2026, 2, 26),
            status="open",
        )
        self.student = Student.objects.create(
            full_name="Ahmed Mohamed",
            phone_number="+20101234567",
            address="Alexandria, Egypt",
            passport_number="P1234567",
            level=self.level,
        )

    def test_open_exam_is_listed_with_sections_and_file_url(self):
        response = self.client.get("/api/exams/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["name"], "Level 6 Final Exam")
        self.assertEqual(response.data[0]["level"], "Level 6")
        self.assertIsNone(response.data[0]["exam_file_url"])

    def test_student_can_submit_supported_answer_file_once(self):
        answer_file = SimpleUploadedFile("answers.pdf", b"%PDF-1.4", content_type="application/pdf")

        response = self.client.post(
            "/api/exams/submissions/",
            {"student_code": self.student.student_code, "exam": self.exam.id, "answer_file": answer_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "submitted")

    def test_duplicate_submission_is_rejected(self):
        self.student.exam_submissions.create(
            exam=self.exam,
            answer_file=SimpleUploadedFile("answers.pdf", b"%PDF-1.4", content_type="application/pdf"),
        )
        answer_file = SimpleUploadedFile("answers-again.pdf", b"%PDF-1.4", content_type="application/pdf")

        response = self.client.post(
            "/api/exams/submissions/",
            {"student_code": self.student.student_code, "exam": self.exam.id, "answer_file": answer_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"], "duplicate_submission")

    def test_unsupported_answer_file_is_rejected(self):
        answer_file = SimpleUploadedFile("answers.txt", b"not an answer sheet", content_type="text/plain")

        response = self.client.post(
            "/api/exams/submissions/",
            {"student_code": self.student.student_code, "exam": self.exam.id, "answer_file": answer_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "unsupported_answer_file_type")
