import datetime
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from apps.attempts.models import ExamAttempt
from apps.exams.models import Exam, Level
from apps.students.models import Student, StudentPromotion
from apps.students.promotions import assessment_promotion_status, promote_student_from_attempt
from apps.teachers.models import TeacherAssessment, TeacherAssessmentConfig


class StudentAdminBulkLevelAssignmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.current_level = Level.objects.create(name="Current level", order=1)
        self.target_level = Level.objects.create(name="Next exam level", order=2)
        self.inactive_level = Level.objects.create(name="Inactive level", order=3, is_active=False)
        self.students = [
            Student.objects.create(
                full_name=f"Student {number}",
                phone_number=f"100{number}",
                address="Cairo",
                passport_number=f"BULK-{number}",
                level=self.current_level,
            )
            for number in range(2)
        ]
        self.admin_user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="secret"
        )
        self.client.force_login(self.admin_user)

    def test_admin_can_assign_selected_roster_to_level(self):
        response = self.client.post(
            "/admin/students/studentpromotionroster/",
            {
                "action": "assign_selected_students_to_level",
                "target_level": str(self.target_level.id),
                "select_across": "0",
                "_selected_action": [student.id for student in self.students],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(Student.objects.order_by("id").values_list("level_id", flat=True)),
            [self.target_level.id, self.target_level.id],
        )

    def test_admin_bulk_assignment_rejects_inactive_level(self):
        response = self.client.post(
            "/admin/students/studentpromotionroster/",
            {
                "action": "assign_selected_students_to_level",
                "target_level": str(self.inactive_level.id),
                "select_across": "0",
                "_selected_action": [student.id for student in self.students],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Student.objects.filter(level=self.current_level).count(), 2)

    def test_admin_can_add_a_student_with_generated_code(self):
        response = self.client.post(
            "/admin/students/studentpromotionroster/add/",
            {
                "full_name": "New Student",
                "phone_number": "123456",
                "address": "Cairo",
                "passport_number": "ADMIN-NEW-1",
                "level": str(self.current_level.id),
                "preferred_language": "ar",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        added_student = Student.objects.get(passport_number="ADMIN-NEW-1")
        self.assertRegex(added_student.student_code, r"^\d{8}$")
        self.assertEqual(added_student.level, self.current_level)


class StudentRegistrationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.level_five = Level.objects.create(name="Level 5", order=5)
        self.level_six = Level.objects.create(name="Level 6", order=6)

    def test_registration_returns_code_without_passport(self):
        response = self.client.post(
            "/api/students/register/",
            {
                "full_name": "Ahmed Mohamed",
                "phone_number": "+20101234567",
                "address": "Alexandria, Egypt",
                "passport_number": "P1234567",
                "level_id": self.level_five.id,
                "preferred_language": "ar",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertRegex(response.data["student_code"], r"^\d{8}$")
        self.assertNotIn("passport_number", response.data)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(Student.objects.get().level, self.level_five)

    def test_registration_requires_level(self):
        response = self.client.post(
            "/api/students/register/",
            {
                "full_name": "Ahmed Mohamed",
                "phone_number": "+20101234567",
                "address": "Alexandria, Egypt",
                "passport_number": "P1234567",
                "preferred_language": "ar",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("level_id", response.data)

    def test_registration_rejects_duplicate_passport_number(self):
        payload = {
            "full_name": "Ahmed Mohamed",
            "phone_number": "+20101234567",
            "address": "Alexandria, Egypt",
            "passport_number": "P1234567",
            "level_id": self.level_five.id,
            "preferred_language": "ar",
        }
        first_response = self.client.post("/api/students/register/", payload, format="json")
        duplicate_payload = {
            **payload,
            "full_name": "Another Student",
            "passport_number": " p1234567 ",
        }

        duplicate_response = self.client.post(
            "/api/students/register/", duplicate_payload, format="json"
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(duplicate_response.status_code, 400)
        self.assertIn("passport_number", duplicate_response.data)
        self.assertEqual(Student.objects.count(), 1)

    def test_level_options_are_ordered(self):
        response = self.client.get("/api/students/levels/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [{"id": self.level_five.id, "name": "Level 5"}, {"id": self.level_six.id, "name": "Level 6"}])

    def test_level_options_exclude_inactive_levels(self):
        self.level_six.is_active = False
        self.level_six.save(update_fields=("is_active",))

        response = self.client.get("/api/students/levels/")

        self.assertEqual(response.data, [{"id": self.level_five.id, "name": "Level 5"}])

    def test_registration_allows_configured_frontend_origin(self):
        response = self.client.post(
            "/api/students/register/",
            {
                "full_name": "Ahmed Mohamed",
                "phone_number": "+20101234567",
                "address": "Alexandria, Egypt",
                "passport_number": "P1234567",
                "level_id": self.level_five.id,
                "preferred_language": "ar",
            },
            HTTP_ORIGIN="http://localhost:5173",
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"],
            "http://localhost:5173",
        )

    def test_level_lookup_returns_only_public_student_level_data(self):
        level = Level.objects.create(name="Level 7", order=7)
        student = Student.objects.create(
            full_name="Ahmed Mohamed",
            phone_number="+20101234567",
            address="Alexandria, Egypt",
            passport_number="P1234567",
            level=level,
        )

        response = self.client.get(f"/api/students/{student.student_code}/level/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["level"], "Level 7")
        self.assertEqual(response.data["full_name"], "Ahmed Mohamed")
        self.assertNotIn("passport_number", response.data)

    def test_codes_are_random_and_unique(self):
        first = Student.objects.create(
            full_name="First Student",
            phone_number="+20101234567",
            address="Alexandria, Egypt",
            passport_number="P1234567",
            level=self.level_five,
        )
        second = Student.objects.create(
            full_name="Second Student",
            phone_number="+20101234568",
            address="Alexandria, Egypt",
            passport_number="P1234568",
            level=self.level_five,
        )

        self.assertRegex(first.student_code, r"^\d{8}$")
        self.assertNotEqual(first.student_code, second.student_code)

    def test_generated_code_can_include_a_leading_zero(self):
        with mock.patch("apps.students.services.secrets.randbelow", return_value=1234567):
            student = Student.objects.create(
                full_name="Leading Zero Student",
                phone_number="+20101234569",
                address="Cairo, Egypt",
                passport_number="P1234570",
                level=self.level_five,
            )

        self.assertEqual(student.student_code, "01234567")

    def test_level_lookup_returns_null_for_unassigned_student(self):
        student = Student.objects.create(
            full_name="Ahmed Mohamed",
            phone_number="+20101234567",
            address="Alexandria, Egypt",
            passport_number="P1234567",
        )

        response = self.client.get(f"/api/students/{student.student_code.lower()}/level/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["level"])


class StudentPromotionTests(TestCase):
    def setUp(self):
        self.first_level = Level.objects.create(name="Level 1", order=1)
        self.next_level = Level.objects.create(name="Level 2", order=2)
        self.student = Student.objects.create(
            full_name="Promotion Student",
            phone_number="123",
            address="Cairo",
            passport_number="PROMO-1",
            level=self.first_level,
        )
        self.exam = Exam.objects.create(
            level=self.first_level,
            name="Online exam",
            max_score=100,
            exam_date=datetime.date(2026, 10, 2),
            status="open",
        )
        self.config = TeacherAssessmentConfig.objects.create(
            level=self.first_level,
            written_max=100,
            activity_dictation_max=50,
            oral_max=50,
        )

    def make_attempt(self, score=Decimal("50")):
        return ExamAttempt.objects.create(
            student=self.student,
            exam=self.exam,
            status="submitted",
            submitted_at=timezone.now(),
            score=score,
            max_score=100,
            percentage=score,
        )

    def make_assessment(self, activity=Decimal("25"), oral=Decimal("25"), complete=True):
        return TeacherAssessment.objects.create(
            student=self.student,
            level=self.first_level,
            activity_dictation_score=activity,
            oral_score=oral,
            is_complete=complete,
            completed_at=timezone.now() if complete else None,
        )

    def test_exactly_fifty_percent_promotes_and_records_score_snapshot(self):
        attempt = self.make_attempt(Decimal("50"))
        self.make_assessment(Decimal("25"), Decimal("25"))

        outcome = promote_student_from_attempt(attempt.id)

        self.student.refresh_from_db()
        self.assertEqual(outcome.status, "promoted")
        self.assertEqual(self.student.level, self.next_level)
        self.assertEqual(StudentPromotion.objects.get().percentage, Decimal("50.00"))
        self.assertEqual(StudentPromotion.objects.get().total_score, Decimal("100.00"))

    def test_below_fifty_percent_does_not_promote(self):
        attempt = self.make_attempt(Decimal("49.99"))
        self.make_assessment(Decimal("25"), Decimal("25"))

        outcome = promote_student_from_attempt(attempt.id)

        self.student.refresh_from_db()
        self.assertEqual(outcome.reason, "below_threshold")
        self.assertEqual(self.student.level, self.first_level)
        self.assertFalse(StudentPromotion.objects.exists())

    def test_submitted_zero_is_a_valid_score(self):
        attempt = self.make_attempt(Decimal("0"))
        self.make_assessment(Decimal("50"), Decimal("50"))

        outcome = promote_student_from_attempt(attempt.id)

        self.student.refresh_from_db()
        self.assertEqual(outcome.status, "promoted")
        self.assertEqual(outcome.promotion.written_score, Decimal("0.00"))
        self.assertEqual(self.student.level, self.next_level)

    def test_missing_or_incomplete_teacher_scores_do_not_promote(self):
        attempt = self.make_attempt()
        assessment = self.make_assessment(complete=False)

        outcome = promote_student_from_attempt(attempt.id)

        self.assertEqual(outcome.reason, "teacher_assessment_incomplete")
        self.assertEqual(assessment_promotion_status(assessment), "incomplete")
        self.assertEqual(self.student.level, self.first_level)

    def test_missing_teacher_assessment_does_not_promote(self):
        attempt = self.make_attempt()

        outcome = promote_student_from_attempt(attempt.id)

        self.assertEqual(outcome.reason, "teacher_assessment_incomplete")
        self.assertEqual(self.student.level, self.first_level)

    def test_completed_teacher_scores_wait_for_online_exam(self):
        assessment = self.make_assessment()

        self.assertEqual(assessment_promotion_status(assessment), "awaiting_exam")

    def test_no_next_active_level_does_not_promote(self):
        self.next_level.is_active = False
        self.next_level.save(update_fields=("is_active",))
        attempt = self.make_attempt()
        self.make_assessment()

        outcome = promote_student_from_attempt(attempt.id)

        self.assertEqual(outcome.reason, "no_next_active_level")
        self.assertEqual(self.student.level, self.first_level)

    def test_repeat_request_returns_existing_promotion(self):
        attempt = self.make_attempt()
        self.make_assessment()

        first_outcome = promote_student_from_attempt(attempt.id)
        repeated_outcome = promote_student_from_attempt(attempt.id)

        self.assertEqual(first_outcome.status, "promoted")
        self.assertEqual(repeated_outcome.status, "already_promoted")
        self.assertEqual(StudentPromotion.objects.count(), 1)

    def test_older_level_attempt_cannot_promote_student_again(self):
        original_attempt = self.make_attempt()
        self.make_assessment()
        promote_student_from_attempt(original_attempt.id)
        older_exam = Exam.objects.create(
            level=self.first_level,
            name="Earlier level retake",
            max_score=100,
            exam_date=datetime.date(2026, 10, 3),
            status="open",
        )
        older_attempt = ExamAttempt.objects.create(
            student=self.student,
            exam=older_exam,
            status="submitted",
            submitted_at=timezone.now(),
            score=100,
            max_score=100,
            percentage=100,
        )

        outcome = promote_student_from_attempt(older_attempt.id)

        self.assertEqual(outcome.reason, "student_level_mismatch")
        self.assertEqual(StudentPromotion.objects.count(), 1)
        assessment = TeacherAssessment.objects.get(student=self.student, level=self.first_level)
        assessment.oral_score = 30
        assessment.save(update_fields=("oral_score",))
        assessment.refresh_from_db()
        self.assertEqual(assessment_promotion_status(assessment), "review_required")

    def test_teacher_scores_first_promotes_when_exam_arrives(self):
        self.make_assessment()
        attempt = self.make_attempt()

        ready_outcome = promote_student_from_attempt(attempt.id)

        self.assertEqual(ready_outcome.status, "promoted")

    def test_online_exam_first_promotes_when_teacher_scores_arrive(self):
        attempt = self.make_attempt()

        waiting_outcome = promote_student_from_attempt(attempt.id)
        self.make_assessment()
        ready_outcome = promote_student_from_attempt(attempt.id)

        self.assertEqual(waiting_outcome.reason, "teacher_assessment_incomplete")
        self.assertEqual(ready_outcome.status, "promoted")


class ConcurrentStudentPromotionTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_requests_create_only_one_promotion(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        from django.db import close_old_connections

        level = Level.objects.create(name="Concurrent Level 1", order=1)
        next_level = Level.objects.create(name="Concurrent Level 2", order=2)
        student = Student.objects.create(
            full_name="Concurrent Student",
            phone_number="456",
            address="Cairo",
            passport_number="PROMO-CONCURRENT",
            level=level,
        )
        exam = Exam.objects.create(
            level=level,
            name="Online exam",
            max_score=100,
            exam_date=datetime.date(2026, 10, 2),
            status="open",
        )
        attempt = ExamAttempt.objects.create(
            student=student,
            exam=exam,
            status="submitted",
            submitted_at=timezone.now(),
            score=50,
            max_score=100,
            percentage=50,
        )
        TeacherAssessmentConfig.objects.create(
            level=level, written_max=100, activity_dictation_max=50, oral_max=50
        )
        TeacherAssessment.objects.create(
            student=student,
            level=level,
            activity_dictation_score=25,
            oral_score=25,
            is_complete=True,
            completed_at=timezone.now(),
        )
        start_together = Barrier(2)

        def promote_concurrently():
            close_old_connections()
            try:
                start_together.wait()
                return promote_student_from_attempt(attempt.id).status
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: promote_concurrently(), range(2)))

        student.refresh_from_db()
        self.assertCountEqual(outcomes, ["promoted", "already_promoted"])
        self.assertEqual(student.level, next_level)
        self.assertEqual(StudentPromotion.objects.count(), 1)
