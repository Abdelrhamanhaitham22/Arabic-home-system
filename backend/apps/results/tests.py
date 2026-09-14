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
        Result.objects.create(student=self.student, exam=self.exam, score=120, published=True)

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

    def test_unpublished_result_is_hidden_from_public_lookup(self):
        Result.objects.create(student=self.student, exam=self.exam, score=120)

        response = self.client.get(f"/api/results/{self.student.student_code}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])

    def test_publishing_section_scores_calculates_total_and_marks_submission_reviewed(self):
        from apps.exams.models import ExamSection
        from .models import ExamSubmission, SectionScore

        self.exam.max_score = 30
        self.exam.save(update_fields=("max_score",))
        reading = ExamSection.objects.create(exam=self.exam, name="Reading", max_score=15, order=1)
        grammar = ExamSection.objects.create(exam=self.exam, name="Grammar", max_score=15, order=2)
        submission = ExamSubmission.objects.create(student=self.student, exam=self.exam)
        result = Result.objects.create(student=self.student, exam=self.exam, score=0, submission=submission)
        SectionScore.objects.create(result=result, section=reading, score=12)
        SectionScore.objects.create(result=result, section=grammar, score=14)

        result.publish()
        result.refresh_from_db()
        submission.refresh_from_db()

        self.assertEqual(result.score, 26)
        self.assertTrue(result.published)
        self.assertEqual(submission.status, "reviewed")
        self.assertIsNotNone(submission.reviewed_at)

    def test_publishing_incomplete_section_scores_is_rejected(self):
        from apps.exams.models import ExamSection

        ExamSection.objects.create(exam=self.exam, name="Reading", max_score=15, order=1)
        result = Result.objects.create(student=self.student, exam=self.exam, score=0)

        with self.assertRaises(ValidationError):
            result.publish()

    def test_section_score_above_section_limit_is_rejected(self):
        from apps.exams.models import ExamSection
        from .models import SectionScore

        section = ExamSection.objects.create(exam=self.exam, name="Reading", max_score=15, order=1)
        result = Result.objects.create(student=self.student, exam=self.exam, score=0)
        section_score = SectionScore(result=result, section=section, score=16)

        with self.assertRaises(ValidationError):
            section_score.full_clean()

    def test_submission_creates_draft_result_and_enters_review(self):
        from apps.exams.models import ExamSection
        from .models import ExamSubmission

        ExamSection.objects.create(exam=self.exam, name="Reading", max_score=15, order=1)
        submission = ExamSubmission.objects.create(student=self.student, exam=self.exam)

        result, created = submission.create_draft_result()

        self.assertTrue(created)
        self.assertEqual(result.submission, submission)
        self.assertEqual(result.score, 0)
        self.assertEqual(submission.status, "under_review")

    def test_restarting_review_reuses_existing_result(self):
        from .models import ExamSubmission

        submission = ExamSubmission.objects.create(student=self.student, exam=self.exam)
        first_result, first_created = submission.create_draft_result()
        second_result, second_created = submission.create_draft_result()

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first_result.pk, second_result.pk)
