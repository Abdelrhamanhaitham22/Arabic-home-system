import datetime
from decimal import Decimal
from io import BytesIO
from io import StringIO

from django.core.management import CommandError, call_command
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.forms import modelform_factory
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from docx import Document

from apps.students.models import Student

from .generator import create_exam
from .models import Exam, ExamQuestion, Level, Question, QuestionChoice, QuestionSource, Subject
from .importers import import_question_bank
from .word_importers import import_question_banks_from_word


def word_file(filename, question, correct="True"):
    document = Document()
    for line in (
        f"Question: {question}",
        "Option 1: True",
        "Option 2: False",
        f"Correct answer: {correct}",
        "Question type: true_false",
        "",
    ):
        document.add_paragraph(line)
    content = BytesIO()
    document.save(content)
    return SimpleUploadedFile(
        filename,
        content.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


class QuestionBankTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(name="Level 6", order=6)
        self.exam = Exam.objects.create(
            level=self.level,
            name="Level 6 Online Exam",
            max_score=50,
            exam_date=datetime.date(2026, 9, 30),
        )
    def test_question_belongs_to_level_question_bank(self):
        question = Question.objects.create(
            level=self.level,
            prompt="Is this true?",
            question_type="true_false",
            points=1,
            order=1,
            bank_order=1,
        )

        self.assertEqual(list(self.level.question_bank.all()), [question])
        self.assertTrue(question.is_active)

    def test_subject_belongs_to_level_and_question_can_reference_source(self):
        subject = Subject.objects.create(level=self.level, name="نحو")
        source = QuestionSource.objects.create(
            level=self.level,
            subject=subject,
            file=SimpleUploadedFile("grammar.docx", b"questions"),
            original_filename="grammar.docx",
        )
        question = Question.objects.create(
            level=self.level,
            subject=subject,
            source=source,
            prompt="Is this true?",
            question_type="true_false",
            points=1,
            order=1,
            bank_order=1,
        )

        self.assertEqual(subject.level, self.level)
        self.assertEqual(source.question_count, 1)
        self.assertEqual(question.source, source)

    def test_source_rejects_subject_from_another_level(self):
        other_level = Level.objects.create(name="Level 7", order=7)
        subject = Subject.objects.create(level=other_level, name="صرف")
        source = QuestionSource(level=self.level, subject=subject, original_filename="morphology.docx")

        with self.assertRaises(ValidationError):
            source.full_clean()

    def test_multiple_word_files_create_sources_and_link_questions(self):
        subject = Subject.objects.create(level=self.level, name="نحو")
        imported_count = import_question_banks_from_word(
            self.level,
            subject,
            [word_file("grammar-one.docx", "First question"), word_file("grammar-two.docx", "Second question")],
        )

        self.assertEqual(imported_count, 2)
        self.assertEqual(QuestionSource.objects.filter(level=self.level, subject=subject).count(), 2)
        self.assertEqual(self.level.question_bank.filter(source__isnull=False).count(), 2)
        filenames = set(self.level.question_bank.values_list("source__original_filename", flat=True))
        self.assertEqual(filenames, {"grammar-one.docx", "grammar-two.docx"})

    def test_word_import_rejects_subject_from_another_level_without_saving(self):
        other_level = Level.objects.create(name="Level 7", order=7)
        subject = Subject.objects.create(level=other_level, name="صرف")

        with self.assertRaises(ValidationError):
            import_question_banks_from_word(self.level, subject, [word_file("morphology.docx", "Question")])

        self.assertEqual(QuestionSource.objects.count(), 0)
        self.assertEqual(self.level.question_bank.count(), 0)

    def test_exam_generator_saves_allocations_and_points_per_question(self):
        subject = Subject.objects.create(level=self.level, name="نحو")
        source = QuestionSource.objects.create(
            level=self.level,
            subject=subject,
            file=SimpleUploadedFile("grammar.docx", b"questions"),
            original_filename="grammar.docx",
        )
        for order in range(1, 3):
            Question.objects.create(
                level=self.level,
                subject=subject,
                source=source,
                prompt=f"Question {order}",
                question_type="true_false",
                points=1,
                order=order,
                bank_order=order,
            )

        exam = create_exam({
            "level": self.level,
            "name": "Generated exam",
            "max_score": Decimal("3.00"),
            "question_count": 2,
            "exam_date": datetime.date(2026, 10, 3),
            "allocations": [{"source": source, "question_count": 2}],
        })

        self.assertEqual(exam.source_allocations.get().question_count, 2)
        self.assertEqual(exam.selected_questions.count(), 2)
        self.assertEqual(
            list(exam.selected_questions.values_list("display_order", flat=True)),
            [1, 2],
        )
        self.assertEqual(exam.max_score / exam.question_count, Decimal("1.50"))

    def test_exam_generator_rejects_allocation_above_source_capacity(self):
        subject = Subject.objects.create(level=self.level, name="صرف")
        source = QuestionSource.objects.create(
            level=self.level,
            subject=subject,
            file=SimpleUploadedFile("morphology.docx", b"questions"),
            original_filename="morphology.docx",
        )

        with self.assertRaises(ValidationError):
            create_exam({
                "level": self.level,
                "name": "Invalid exam",
                "max_score": Decimal("75"),
                "question_count": 50,
                "exam_date": datetime.date(2026, 10, 3),
                "allocations": [{"source": source, "question_count": 50}],
            })

    def test_exam_management_lists_and_duplicates_exam(self):
        admin = get_user_model().objects.create_superuser("owner", "owner@example.com", "password")
        subject = Subject.objects.create(level=self.level, name="نحو")
        source = QuestionSource.objects.create(
            level=self.level,
            subject=subject,
            file=SimpleUploadedFile("grammar.docx", b"questions"),
            original_filename="grammar.docx",
        )
        question = Question.objects.create(
            level=self.level,
            subject=subject,
            source=source,
            prompt="Question",
            question_type="true_false",
            points=1,
            order=1,
            bank_order=1,
        )
        generated = create_exam({
            "level": self.level,
            "name": "Generated exam",
            "max_score": Decimal("1.00"),
            "question_count": 1,
            "exam_date": datetime.date(2026, 10, 3),
            "allocations": [{"source": source, "question_count": 1}],
        })
        self.client.force_login(admin)

        listed = self.client.get("/api/exams/admin-management/exams/")
        duplicated = self.client.post(
            "/api/exams/admin-management/exams/",
            {"exam_id": generated.id},
            format="json",
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(duplicated.status_code, 201)
        duplicate = Exam.objects.exclude(id=generated.id).get()
        self.assertEqual(duplicate.selected_questions.count(), 1)
        self.assertEqual(duplicate.selected_questions.get().question_id, question.id)

    def test_exam_status_is_locked_after_attempt_starts(self):
        admin = get_user_model().objects.create_superuser("owner", "owner@example.com", "password")
        student = Student.objects.create(full_name="Student", phone_number="1", address="Cairo", passport_number="P-1", level=self.level)
        Exam.objects.filter(id=self.exam.id).update(status="open")
        from apps.attempts.models import ExamAttempt

        ExamAttempt.objects.create(student=student, exam=self.exam, max_score=Decimal("50.00"))
        self.client.force_login(admin)

        response = self.client.post(
            f"/api/exams/admin-generator/exams/{self.exam.id}/status/",
            {"status": "closed"},
            format="json",
        )

        self.assertEqual(response.status_code, 409)

    def test_question_bank_order_is_unique_per_level(self):
        Question.objects.create(
            level=self.level,
            prompt="First question",
            question_type="true_false",
            points=1,
            order=1,
            bank_order=1,
        )

        with self.assertRaises(IntegrityError):
            Question.objects.create(
                level=self.level,
                prompt="Duplicate order",
                question_type="true_false",
                points=1,
                order=2,
                bank_order=1,
            )

    def test_objective_questions_cannot_use_answer_text(self):
        question = Question(
            level=self.level,
            prompt="Is this true?",
            question_type="true_false",
            points=1,
            order=1,
            answer_text="True",
        )

        with self.assertRaises(ValidationError):
            question.full_clean()

    def test_incomplete_question_bank_reports_missing_requirements(self):
        errors = self.level.question_bank_errors()

        self.assertIn("The active question bank must contain between 100 and 300 questions.", errors)
        self.assertIn("The active question bank must contain at least 25 true/false questions.", errors)
        self.assertIn("The active question bank must contain at least 25 multiple-choice questions.", errors)

    def test_question_bank_requires_exactly_one_correct_choice(self):
        question = Question.objects.create(
            level=self.level,
            prompt="Choose one.",
            question_type="multiple_choice",
            points=1,
            order=1,
            bank_order=1,
        )
        QuestionChoice.objects.create(question=question, text="First", order=1)
        QuestionChoice.objects.create(question=question, text="Second", order=2)

        self.assertIn("Question %s must have exactly one correct answer." % question.id, self.level.question_bank_errors())

    def test_complete_question_bank_is_valid(self):
        for bank_order in range(1, 201):
            question_type = "true_false" if bank_order <= 100 else "multiple_choice"
            question = Question.objects.create(
                level=self.level,
                prompt=f"Question {bank_order}",
                question_type=question_type,
                points=1,
                order=bank_order,
                bank_order=bank_order,
            )
            QuestionChoice.objects.create(question=question, text="Correct", order=1, is_correct=True)
            QuestionChoice.objects.create(question=question, text="Wrong", order=2)

        self.assertEqual(self.level.question_bank_errors(), [])

        self.exam.status = "open"
        self.exam.full_clean()

    def test_csv_import_creates_questions_and_choices(self):
        csv_file = BytesIO(
            b"bank_order,prompt,question_type,points,choice_1,choice_1_correct,choice_2,choice_2_correct,choice_3,choice_3_correct,choice_4,choice_4_correct\n"
            b"1,Is Arabic a language?,true_false,1,True,true,False,false,,,,\n"
            b"2,Choose Cairo,multiple_choice,1,Cairo,true,Alexandria,false,Giza,false, Luxor,false\n"
        )
        imported_count = import_question_bank(self.level, csv_file)

        self.assertEqual(imported_count, 2)
        self.assertEqual(self.level.question_bank.count(), 2)
        self.assertEqual(self.level.question_bank.get(bank_order=2).choices.filter(is_correct=True).count(), 1)

    def test_csv_import_rejects_invalid_true_false_row_without_partial_save(self):
        csv_file = BytesIO(
            b"bank_order,prompt,question_type,points,choice_1,choice_1_correct,choice_2,choice_2_correct,choice_3,choice_3_correct,choice_4,choice_4_correct\n"
            b"1,Valid question,true_false,1,True,true,False,false,,,,\n"
            b"2,Invalid question,true_false,1,True,true,False,false,Maybe,false,,\n"
        )

        with self.assertRaises(ValidationError):
            import_question_bank(self.level, csv_file)

        self.assertEqual(self.level.question_bank.count(), 0)

    def test_csv_import_rejects_existing_bank_order(self):
        Question.objects.create(
            level=self.level, prompt="Existing", question_type="true_false", points=1,
            order=1, bank_order=1,
        )
        csv_file = BytesIO(
            b"bank_order,prompt,question_type,points,choice_1,choice_1_correct,choice_2,choice_2_correct,choice_3,choice_3_correct,choice_4,choice_4_correct\n"
            b"1,Duplicate,true_false,1,True,true,False,false,,,,\n"
        )

        with self.assertRaises(ValidationError):
            import_question_bank(self.level, csv_file)

        self.assertEqual(self.level.question_bank.count(), 1)


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
        multiple_choice = Question.objects.create(
            level=self.level,
            prompt="Choose the greeting.",
            question_type="multiple_choice",
            points=2,
            order=1,
        )
        QuestionChoice.objects.create(question=multiple_choice, text="مرحبا", order=1, is_correct=True)
        QuestionChoice.objects.create(question=multiple_choice, text="وداعا", order=2)
        QuestionChoice.objects.create(question=multiple_choice, text="Another", order=3)
        true_false = Question.objects.create(
            level=self.level,
            prompt="Is this true?",
            question_type="true_false",
            points=5,
            order=2,
        )
        QuestionChoice.objects.create(question=true_false, text="True", order=1, is_correct=True)
        QuestionChoice.objects.create(question=true_false, text="False", order=2)
        for bank_order in range(3, 201):
            question_type = "true_false" if bank_order <= 100 else "multiple_choice"
            question = Question.objects.create(
                level=self.level,
                prompt=f"Bank question {bank_order}",
                question_type=question_type,
                points=1,
                order=bank_order,
                bank_order=bank_order,
            )
            QuestionChoice.objects.create(question=question, text="Correct", order=1, is_correct=True)
            QuestionChoice.objects.create(question=question, text="Wrong", order=2)
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
        self.assertNotIn("sections", response.data)
        self.assertEqual(response.data["max_score"], 100)
        self.assertNotIn("questions", response.data)

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

    def test_incomplete_question_bank_hides_exam_and_blocks_detail(self):
        question_ids = list(Question.objects.filter(level=self.level).order_by("id").values_list("id", flat=True)[:101])
        Question.objects.filter(id__in=question_ids).delete()

        list_response = self.client.get(f"/api/exams/?student_code={self.student.student_code}")
        detail_response = self.client.get(
            f"/api/exams/{self.exam.id}/?student_code={self.student.student_code}"
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data, [])
        self.assertEqual(detail_response.status_code, 409)
        self.assertEqual(detail_response.data["error"], "question_bank_incomplete")


class SeedLevel6ExamCommandTests(TestCase):
    def test_seed_creates_canonical_draft_exam(self):
        output = StringIO()
        call_command("seed_level_6_exam", "--exam-date", "2026-10-01", stdout=output)
        exam = Exam.objects.get(name="Level 6 Final Exam")
        self.assertEqual(exam.level.name, "Level 6")
        self.assertEqual(exam.max_score, 50)
        self.assertEqual(exam.exam_date, datetime.date(2026, 10, 1))
        self.assertEqual(exam.status, "draft")
        self.assertNotIn("section", output.getvalue().lower())

    def test_seed_is_idempotent_and_open_is_explicit(self):
        call_command("seed_level_6_exam", "--exam-date", "2026-10-01")
        with self.assertRaises(CommandError):
            call_command("seed_level_6_exam", "--exam-date", "2026-10-01", "--open")
        self.assertEqual(Exam.objects.count(), 1)
        self.assertEqual(Exam.objects.get().status, "draft")

    def test_open_exam_form_reports_incomplete_bank_without_server_error(self):
        level = Level.objects.create(name="Level 6", order=6)
        form = modelform_factory(Exam, fields="__all__")(
            data={
                "level": level.pk,
                "name": "Level 6 Final Exam",
                "max_score": 50,
                "exam_date": "2026-10-01",
                "status": "open",
                "opens_at": "",
                "closes_at": "",
                "time_limit_minutes": 45,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("level", form.errors)
        self.assertIn("between 100 and 300", form.errors["level"][0])
