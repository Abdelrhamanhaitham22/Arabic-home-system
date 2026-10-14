import unicodedata
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.shortcuts import get_object_or_404

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attempts.models import ExamAttempt
from apps.core.services import has_staff_role, record_audit
from apps.students.models import Student
from apps.students.promotions import assessment_promotion_status, promote_student_from_attempt

from .models import TeacherAssessment, TeacherAssessmentConfig, TeacherProfile


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
        assigned_levels = self.assigned_levels_for(profile, request.query_params.get("level_id"))
        if isinstance(assigned_levels, Response):
            return assigned_levels
        return Response(self.serialize_portal(profile, request.user, assigned_levels))

    @staticmethod
    def assigned_levels_for(profile, selected_level_id):
        levels = list(profile.levels.all())
        if not selected_level_id:
            return levels
        if not selected_level_id.isdigit() or not profile.levels.filter(id=selected_level_id).exists():
            return Response(
                {"detail": "You can only filter by an assigned level."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return [level for level in levels if level.id == int(selected_level_id)]

    @classmethod
    def serialize_portal(cls, profile, user, assigned_levels):
        assigned_level_ids = [level.id for level in assigned_levels]
        students = cls.students_for_levels(assigned_level_ids)
        assessment_records = cls.assessments_for_students(students, assigned_level_ids)
        assessment_by_student = cls.preferred_assessments(students, assessment_records)
        configs = {
            config.level_id: config
            for config in TeacherAssessmentConfig.objects.filter(level_id__in=assigned_level_ids)
        }
        return {
            "username": user.get_username(),
            "levels": [{"id": level.id, "name": level.name} for level in assigned_levels],
            "students": [
                cls.serialize_student(student, assessment_by_student.get(student.id))
                for student in students
            ],
            "assessment_configs": [
                cls.serialize_config(configs.get(level.id), level) for level in assigned_levels
            ],
            "assessments": [cls.serialize_assessment(item) for item in assessment_records],
        }

    @staticmethod
    def students_for_levels(assigned_level_ids):
        return list(
            Student.objects.filter(
                Q(level_id__in=assigned_level_ids)
                | Q(teacher_assessments__level_id__in=assigned_level_ids)
            ).select_related("level").distinct().order_by("full_name")
        )

    @staticmethod
    def assessments_for_students(students, assigned_level_ids):
        return list(
            TeacherAssessment.objects.filter(
                student__in=students,
                level_id__in=assigned_level_ids,
            ).select_related("student", "level")
        )

    @staticmethod
    def preferred_assessments(students, assessments):
        ordered_assessments = sorted(
            assessments,
            key=lambda item: (item.level_id == item.student.level_id, item.updated_at),
        )
        return {assessment.student_id: assessment for assessment in ordered_assessments}

    @staticmethod
    def serialize_student(student, assessment=None):
        return {
            "student_code": student.student_code,
            "full_name": student.full_name,
            "level": student.level.name if student.level else None,
            "level_id": student.level_id,
            "assessment_status": assessment_promotion_status(assessment) if assessment else "incomplete",
        }

    @staticmethod
    def serialize_config(config, level):
        return {"level_id": level.id, "level": level.name, "written_max": float(config.written_max) if config else 75, "activity_dictation_max": float(config.activity_dictation_max) if config else 50, "oral_max": float(config.oral_max) if config else 75}

    @staticmethod
    def serialize_assessment(assessment):
        return {
            "student_code": assessment.student.student_code,
            "level_id": assessment.level_id,
            "written_score": float(assessment.written_score),
            "activity_dictation_score": float(assessment.activity_dictation_score),
            "oral_score": float(assessment.oral_score),
            "total_score": float(assessment.total_score),
            "teacher_notes": assessment.teacher_notes,
            "is_complete": assessment.is_complete,
            "completed_at": assessment.completed_at,
            "promotion_status": assessment_promotion_status(assessment),
        }


class TeacherAssessmentView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request, student_code):
        profile = teacher_profile_for(request)
        if profile is None:
            return Response({"detail": "Teacher access required."}, status=status.HTTP_403_FORBIDDEN)
        student = get_object_or_404(Student.objects.select_related("level"), student_code=student_code.upper())
        if not student.level_id or not profile.levels.filter(id=student.level_id).exists():
            return Response({"detail": "You can only assess students in an assigned level."}, status=status.HTTP_403_FORBIDDEN)
        required_scores = ("activity_dictation_score", "oral_score")
        if any(field not in request.data for field in required_scores):
            return Response(
                {"detail": "Both activity/dictation and oral scores are required to complete an assessment."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        config, _ = TeacherAssessmentConfig.objects.get_or_create(level_id=student.level_id)
        values = {}
        for field in ("activity_dictation_score", "oral_score"):
            try:
                value = Decimal(str(request.data.get(field, 0)))
            except (InvalidOperation, TypeError):
                return Response({"detail": f"{field} must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)
            maximum = getattr(config, field.replace("score", "max"))
            if value < 0 or value > maximum:
                return Response({"detail": f"{field} must be between 0 and {maximum}."}, status=status.HTTP_400_BAD_REQUEST)
            values[field] = value
        assessment, _ = TeacherAssessment.objects.update_or_create(
            student=student,
            level_id=student.level_id,
            defaults={
                **values,
                "teacher": request.user,
                "teacher_notes": str(request.data.get("teacher_notes", ""))[:5000],
                "is_complete": True,
                "completed_at": timezone.now(),
            },
        )
        from apps.results.models import Result
        total_score = assessment.total_score
        total_max = config.total_max
        Result.objects.filter(student=student, exam__level_id=student.level_id).update(
            score=total_score,
            max_score=total_max,
            percentage=round((total_score / total_max) * 100, 2) if total_max else 0,
            published=True,
        )
        latest_attempt = ExamAttempt.objects.filter(
            student=student,
            exam__level_id=assessment.level_id,
            status="submitted",
        ).order_by("-submitted_at", "-id").first()
        if latest_attempt:
            promote_student_from_attempt(latest_attempt.id)
        return Response(TeacherMeView.serialize_assessment(assessment))


class TeacherAssessmentConfigView(APIView):
    def get(self, request):
        if not request.user.is_authenticated or not has_staff_role(request.user, "viewer"):
            return Response({"detail": "Staff access required."}, status=status.HTTP_403_FORBIDDEN)
        return Response([serialize_config(config) for config in TeacherAssessmentConfig.objects.select_related("level").order_by("level__order")])

    def patch(self, request, level_id):
        if not request.user.is_authenticated or not has_staff_role(request.user, "administrator"):
            return Response({"detail": "Administrator access required."}, status=status.HTTP_403_FORBIDDEN)
        config, _ = TeacherAssessmentConfig.objects.get_or_create(level_id=level_id)
        for field in ("written_max", "activity_dictation_max", "oral_max"):
            if field in request.data:
                try:
                    value = Decimal(str(request.data[field]))
                except (InvalidOperation, TypeError):
                    return Response({"detail": f"{field} must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)
                if value < 0:
                    return Response({"detail": f"{field} cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
                setattr(config, field, value)
        config.full_clean()
        config.save()
        record_audit(request.user, "teacher-assessment.configured", "Level", level_id)
        return Response(serialize_config(config))


def serialize_config(config):
    return {"level_id": config.level_id, "level": config.level.name, "written_max": float(config.written_max), "activity_dictation_max": float(config.activity_dictation_max), "oral_max": float(config.oral_max), "total_max": float(config.total_max)}
