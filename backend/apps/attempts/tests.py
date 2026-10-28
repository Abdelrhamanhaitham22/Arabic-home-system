import datetime
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.exams.models import Exam, ExamQuestion, Level, Question, QuestionChoice
from apps.results.models import Result
from apps.students.models import Student
from apps.teachers.models import TeacherAssessment


class AttemptApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.level = Level.objects.create(name="Level 6", order=6)
        self.exam = Exam.objects.create(
            level=self.level, name="Online exam", max_score=50,
            exam_date=datetime.date(2026, 10, 2), status="open", time_limit_minutes=45,
        )
        for number in range(1, 201):
            question_type = "true_false" if number <= 100 else "multiple_choice"
            question = Question.objects.create(
                level=self.level, prompt=f"Question {number}", question_type=question_type,
                points=1, order=number, bank_order=number,
            )
            QuestionChoice.objects.create(question=question, text="Correct", order=1, is_correct=True)
            QuestionChoice.objects.create(question=question, text="Wrong", order=2)
        self.student = Student.objects.create(
            full_name="Student One", phone_number="123", address="Cairo", passport_number="PASS-1", level=self.level,
        )
        self.other_student = Student.objects.create(
            full_name="Student Two", phone_number="456", address="Cairo", passport_number="PASS-2", level=self.level,
        )

    def start(self, student=None):
        student = student or self.student
        return self.client.post(f"/api/exams/{self.exam.id}/start/", {"student_code": student.student_code}, format="json")

    def test_start_selects_25_questions_of_each_type_and_hides_keys(self):
        response = self.start()
        self.assertEqual(response.status_code, 200)
        questions = response.data["questions"]
        self.assertEqual(len(questions), 50)
        self.assertEqual(sum(q["question_type_snapshot"] == "true_false" for q in questions), 25)
        self.assertEqual(sum(q["question_type_snapshot"] == "multiple_choice" for q in questions), 25)
        self.assertTrue(all(q["correct_answer"] is None for q in questions))
        self.assertTrue(all("is_correct" not in choice for q in questions for choice in q["choices"]))

    def test_refresh_returns_same_attempt_and_question_set(self):
        first = self.start()
        second = self.start()
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual([q["id"] for q in first.data["questions"]], [q["id"] for q in second.data["questions"]])

    def test_submitted_exam_requires_admin_result_deletion_before_retake(self):
        first = self.start()
        self.client.post(
            f"/api/exam-attempts/{first.data['id']}/submit/",
            {"student_code": self.student.student_code},
            format="json",
        )
        blocked = self.start()
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.data["error"], "exam_already_submitted")
        self.assertEqual(self.start(self.other_student).status_code, 200)

        admin_user = get_user_model().objects.create_superuser(
            username="exam-admin", email="admin@example.com", password="secret"
        )
        self.client.force_login(admin_user)
        result = Result.objects.get(attempt_id=first.data["id"])
        deleted = self.client.post(f"/admin/results/result/{result.pk}/delete/", {"post": "yes"})
        self.assertEqual(deleted.status_code, 302)
        self.assertFalse(Result.objects.filter(pk=result.pk).exists())
        self.client.logout()

        second = self.start()
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(first.data["id"], second.data["id"])
        self.assertNotEqual(
            {question["question_text_snapshot"] for question in first.data["questions"]},
            {question["question_text_snapshot"] for question in second.data["questions"]},
        )

    def test_students_on_same_exam_receive_different_questions_with_same_type_mix(self):
        selected = list(self.level.question_bank.order_by("id")[:50])
        for order, question in enumerate(selected, start=1):
            ExamQuestion.objects.create(exam=self.exam, question=question, display_order=order)

        first = self.start()
        second = self.start(self.other_student)

        first_questions = {question["question_text_snapshot"] for question in first.data["questions"]}
        second_questions = {question["question_text_snapshot"] for question in second.data["questions"]}
        self.assertTrue(first_questions.isdisjoint(second_questions))
        self.assertEqual({question["question_type_snapshot"] for question in first.data["questions"]}, {"true_false"})
        self.assertEqual({question["question_type_snapshot"] for question in second.data["questions"]}, {"true_false"})

    def test_student_cannot_access_another_students_attempt(self):
        attempt = self.start().data["id"]
        response = self.client.get(f"/api/exam-attempts/{attempt}/", {"student_code": self.other_student.student_code})
        self.assertEqual(response.status_code, 404)

    def test_submit_grades_and_creates_result(self):
        TeacherAssessment.objects.create(
            student=self.student,
            level=self.level,
            activity_dictation_score=40,
            oral_score=60,
        )
        attempt = self.start().data
        first_question = attempt["questions"][0]
        correct_choice = next(choice for choice in first_question["choices"] if choice["text"] == "Correct")
        response = self.client.post(
            f"/api/exam-attempts/{attempt['id']}/answers/",
            {"student_code": self.student.student_code, "attempt_question_id": first_question["id"], "selected_choice_id": correct_choice["id"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        submitted = self.client.post(
            f"/api/exam-attempts/{attempt['id']}/submit/", {"student_code": self.student.student_code}, format="json"
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.data["status"], "submitted")
        self.assertIsNotNone(submitted.data["questions"][0]["correct_answer"])
        result = Result.objects.get(attempt_id=attempt["id"])
        self.assertEqual(result.score, 101)
        self.assertTrue(result.published)
        self.assertEqual(result.max_score, 200)
        locked = self.client.post(
            f"/api/exam-attempts/{attempt['id']}/answers/",
            {"student_code": self.student.student_code, "attempt_question_id": first_question["id"], "selected_choice_id": first_question["choices"][1]["id"]},
            format="json",
        )
        self.assertEqual(locked.status_code, 409)
