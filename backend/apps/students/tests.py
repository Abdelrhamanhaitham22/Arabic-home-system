import datetime

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Student


class StudentRegistrationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_registration_returns_code_without_passport(self):
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

        self.assertEqual(response.status_code, 201)
        self.assertRegex(response.data["student_code"], rf"^ST{datetime.date.today().year}\d{{5}}$")
        self.assertNotIn("passport_number", response.data)
        self.assertEqual(Student.objects.count(), 1)

    def test_registration_allows_configured_frontend_origin(self):
        response = self.client.post(
            "/api/students/register/",
            {
                "full_name": "Ahmed Mohamed",
                "phone_number": "+20101234567",
                "address": "Alexandria, Egypt",
                "passport_number": "P1234567",
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
