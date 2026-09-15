import datetime

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Student
from apps.exams.models import Level


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
        self.assertRegex(response.data["student_code"], rf"^ST{datetime.date.today().year}\d{{5}}$")
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

    def test_level_options_are_ordered(self):
        response = self.client.get("/api/students/levels/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [{"id": self.level_five.id, "name": "Level 5"}, {"id": self.level_six.id, "name": "Level 6"}])

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

    def test_level_lookup_returns_null_for_unassigned_student(self):
        student = Student.objects.create(
            full_name="Ahmed Mohamed",
            phone_number="+20101234567",
            address="Alexandria, Egypt",
            passport_number="P1234567",
        )

        response = self.client.get(f"/api/students/{student.student_code}/level/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["level"])
