from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.results.models import ExamSubmission, SectionScore
from apps.students.models import Student

from .models import TeacherProfile


def teacher_profile_for(request):
    return getattr(request.user, "teacher_profile", None)


class TeacherCsrfView(APIView):
    permission_classes = (AllowAny,)

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"detail": "CSRF cookie set.", "csrf_token": get_token(request)})


class TeacherSignupView(APIView):
    permission_classes = (AllowAny,)

    @method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True))
    def post(self, request):
        username = str(request.data.get("username", "")).strip()
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
        username = str(request.data.get("username", "")).strip()
        password = request.data.get("password", "")
        user = authenticate(request, username=username, password=password)
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
        submissions = (
            ExamSubmission.objects.filter(exam__level__in=assigned_levels)
            .select_related("student", "student__level", "exam", "exam__level")
            .prefetch_related("result__section_scores__section")
            .order_by("-submitted_at")
        )
        students = Student.objects.filter(level__in=assigned_levels).select_related("level").order_by("full_name")
        return Response(
            {
                "username": request.user.get_username(),
                "levels": list(profile.levels.values("id", "name")),
                "students": [self.serialize_student(student) for student in students],
                "submissions": [self.serialize_submission(submission) for submission in submissions],
            }
        )

    @staticmethod
    def serialize_student(student):
        return {
            "student_code": student.student_code,
            "full_name": student.full_name,
            "level": student.level.name if student.level else None,
        }

    @staticmethod
    def serialize_submission(submission):
        result = getattr(submission, "result", None)
        return {
            "id": submission.id,
            "student_code": submission.student.student_code,
            "student_name": submission.student.full_name,
            "exam_name": submission.exam.name,
            "level": submission.exam.level.name if submission.exam.level else None,
            "status": submission.status,
            "submitted_at": submission.submitted_at,
            "answer_file_url": f"/teachers/submissions/{submission.id}/file/",
            "sections": [
                {"id": section.id, "name": section.name, "max_score": section.max_score}
                for section in submission.exam.sections.all()
            ],
            "result": TeacherMeView.serialize_result(result) if result else None,
        }

    @staticmethod
    def serialize_result(result):
        return {
            "id": result.id,
            "score": result.score,
            "published": result.published,
            "teacher_notes": result.teacher_notes,
            "sections": [
                {
                    "id": score.section_id,
                    "name": score.section.name,
                    "max_score": score.section.max_score,
                    "score": score.score,
                    "teacher_comment": score.teacher_comment,
                }
                for score in result.section_scores.all()
            ],
        }


def teacher_submission_for(request, submission_id):
    profile = teacher_profile_for(request)
    if profile is None:
        return None
    return get_object_or_404(
        ExamSubmission.objects.select_related("student", "exam", "exam__level"),
        id=submission_id,
        exam__level__in=profile.levels.all(),
    )


class TeacherSubmissionFileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, submission_id):
        submission = teacher_submission_for(request, submission_id)
        if submission is None:
            return Response({"detail": "Teacher access required."}, status=status.HTTP_403_FORBIDDEN)
        if not submission.answer_file:
            raise Http404
        try:
            answer_file = submission.answer_file.open("rb")
        except FileNotFoundError as error:
            raise Http404("The answer file is temporarily unavailable.") from error
        return FileResponse(answer_file, content_type="application/octet-stream")


class TeacherSubmissionGradeView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request, submission_id):
        submission = teacher_submission_for(request, submission_id)
        if submission is None:
            return Response({"detail": "Teacher access required."}, status=status.HTTP_403_FORBIDDEN)

        sections = request.data.get("sections", [])
        if not isinstance(sections, list):
            return Response({"detail": "Sections must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        exam_sections = {section.id: section for section in submission.exam.sections.all()}
        submitted_ids = set()
        validated_scores = []
        for section_data in sections:
            try:
                section_id = int(section_data["section_id"])
                score = int(section_data["score"])
            except (KeyError, TypeError, ValueError):
                return Response({"detail": "Each section needs a section_id and numeric score."}, status=status.HTTP_400_BAD_REQUEST)
            if section_id not in exam_sections:
                return Response({"detail": "Section does not belong to this exam."}, status=status.HTTP_400_BAD_REQUEST)
            if section_id in submitted_ids:
                return Response({"detail": "Each section can only be scored once."}, status=status.HTTP_400_BAD_REQUEST)
            submitted_ids.add(section_id)
            section = exam_sections[section_id]
            if score < 0 or score > section.max_score:
                return Response({"detail": f"Score for {section.name} must be between 0 and {section.max_score}."}, status=status.HTTP_400_BAD_REQUEST)
            validated_scores.append(
                (section, score, str(section_data.get("teacher_comment", "")))
            )

        try:
            with transaction.atomic():
                result, _ = submission.create_draft_result()
                for section, score, teacher_comment in validated_scores:
                    SectionScore.objects.update_or_create(
                        result=result,
                        section=section,
                        defaults={"score": score, "teacher_comment": teacher_comment},
                    )
                if "teacher_notes" in request.data:
                    result.teacher_notes = str(request.data.get("teacher_notes", ""))
                    result.save(update_fields=("teacher_notes", "updated_at"))
                if request.data.get("publish"):
                    result.publish()
        except ValidationError as error:
            return Response({"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TeacherMeView.serialize_result(result))
