import unicodedata

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.students.models import Student

from .models import TeacherProfile


def teacher_profile_for(request):
    return getattr(request.user, "teacher_profile", None)


def normalize_teacher_username(username):
    normalized = unicodedata.normalize("NFKC", str(username))
    return " ".join(normalized.split())


class TeacherCsrfView(APIView):
    permission_classes = (AllowAny,)

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"detail": "CSRF cookie set.", "csrf_token": get_token(request)})


class TeacherSignupView(APIView):
    permission_classes = (AllowAny,)

    @method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True))
    def post(self, request):
        username = normalize_teacher_username(request.data.get("username", ""))
        password = request.data.get("password", "")
        if not username or not password:
            return Response({"detail": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)
        user_model = get_user_model()
        if user_model.objects.filter(username__iexact=username).exists():
            return Response({"detail": "This username is already registered."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(password)
        except ValidationError as error:
            return Response({"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST)
        user = user_model.objects.create_user(username=username, password=password, is_active=True)
        TeacherProfile.objects.create(user=user)
        return Response(
            {"detail": "Your teacher account was created and is waiting for administrator approval."},
            status=status.HTTP_201_CREATED,
        )


class TeacherLoginView(APIView):
    permission_classes = (AllowAny,)

    @method_decorator(ratelimit(key="ip", rate="20/h", method="POST", block=True))
    def post(self, request):
        username = normalize_teacher_username(request.data.get("username", ""))
        password = request.data.get("password", "")
        user_model = get_user_model()
        matched_user = user_model.objects.filter(username__iexact=username).first()
        if matched_user is None:
            matched_user = next(
                (
                    candidate
                    for candidate in user_model.objects.filter(teacher_profile__isnull=False)
                    if normalize_teacher_username(candidate.username).casefold() == username.casefold()
                ),
                None,
            )
        user = authenticate(
            request,
            username=matched_user.get_username() if matched_user else username,
            password=password,
        )
        profile = getattr(user, "teacher_profile", None) if user else None
        if not user or not user.is_active or profile is None:
            return Response(
                {"detail": "Invalid teacher credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not profile.is_approved:
            return Response(
                {"detail": "Your account is waiting for administrator approval."},
                status=status.HTTP_403_FORBIDDEN,
            )
        login(request, user)
        return Response({"username": user.get_username(), "levels": list(profile.levels.values_list("name", flat=True))})


class TeacherLogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if teacher_profile_for(request) is None:
            return Response({"detail": "Teacher access required."}, status=status.HTTP_403_FORBIDDEN)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeacherMeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        profile = teacher_profile_for(request)
        if profile is None:
            return Response({"detail": "Teacher access required."}, status=status.HTTP_403_FORBIDDEN)
        selected_level_id = request.query_params.get("level_id")
        assigned_levels = profile.levels.all()
        if selected_level_id:
            if not selected_level_id.isdigit() or not profile.levels.filter(id=selected_level_id).exists():
                return Response(
                    {"detail": "You can only filter by an assigned level."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            assigned_levels = assigned_levels.filter(id=selected_level_id)
        students = Student.objects.filter(level__in=assigned_levels).select_related("level").order_by("full_name")
        return Response(
            {
                "username": request.user.get_username(),
                "levels": list(profile.levels.values("id", "name")),
                "students": [self.serialize_student(student) for student in students],
            }
        )

    @staticmethod
    def serialize_student(student):
        return {
            "student_code": student.student_code,
            "full_name": student.full_name,
            "level": student.level.name if student.level else None,
        }
