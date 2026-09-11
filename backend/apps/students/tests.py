import datetime

from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Student


class StudentRegistrationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def authenticate_teacher(self):
        teacher = User.objects.create_user(username="teacher", password="pass12345", is_staff=True)
        self.client.force_authenticate(user=teacher)
        self.client.defaults["HTTP_X_CSRFTOKEN"] = get_token(self.client.get("/api/students/csrf/").wsgi_request)

    def test_registration_returns_code_without_passport(self):
        self.authenticate_teacher()
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
        self.authenticate_teacher()
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

    def test_registration_requires_authenticated_staff_user(self):
        response = self.client.post(
            "/api/students/register/",
            {"full_name": "Unauthenticated Student"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_authenticated_staff_user_can_register_student(self):
        self.authenticate_teacher()

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

    def test_staff_login_creates_teacher_session(self):
        User.objects.create_user(username="teacher", password="pass12345", is_staff=True)

        response = self.client.post(
            "/api/students/login/",
            {"username": "teacher", "password": "pass12345"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get("/api/students/session/").status_code,
            200,
        )

    def test_non_staff_login_is_rejected(self):
        User.objects.create_user(username="student", password="pass12345")

        response = self.client.post(
            "/api/students/login/",
            {"username": "student", "password": "pass12345"},
        )

        self.assertEqual(response.status_code, 401)

    @override_settings(CSRF_TRUSTED_ORIGINS=["https://frontend.example.com"])
    def test_staff_login_accepts_csrf_token_from_endpoint(self):
        User.objects.create_user(username="teacher", password="pass12345", is_staff=True)
        csrf_response = self.client.get("/api/students/csrf/")
        response = self.client.post(
            "/api/students/login/",
            {"username": "teacher", "password": "pass12345"},
            HTTP_X_CSRFTOKEN=csrf_response.json()["token"],
            HTTP_ORIGIN="https://frontend.example.com",
        )

        self.assertEqual(response.status_code, 200)
