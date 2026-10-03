from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login, logout
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.students.models import Student
from .generator import create_exam, preview_exam_questions
from .models import Exam, Level, QuestionSource
from .serializers import AvailableExamDetailSerializer, AvailableExamSerializer


class AvailableExamListView(APIView):
    def get(self, request):
        student_code = str(request.query_params.get("student_code", "")).strip().upper()
        if not student_code:
            return Response(
                {"error": "student_code_required", "message": "Enter your student code first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        student = get_object_or_404(Student.objects.select_related("level"), student_code=student_code)
        if not student.level_id:
            return Response(
                {"error": "student_level_required", "message": "Your level has not been assigned yet."},
                status=status.HTTP_409_CONFLICT,
            )
        current_time = timezone.now()
        exams = Exam.objects.filter(status="open", level_id=student.level_id).filter(
            models.Q(opens_at__isnull=True) | models.Q(opens_at__lte=current_time),
            models.Q(closes_at__isnull=True) | models.Q(closes_at__gte=current_time),
        ).select_related("level").prefetch_related("source_allocations__source__questions__choices")
        available_exams = [exam for exam in exams if not self.exam_generation_errors(exam)]
        return Response(AvailableExamSerializer(available_exams, many=True, context={"request": request}).data)

    @staticmethod
    def exam_generation_errors(exam):
        try:
            exam.validate_generation()
        except ValidationError as error:
            return error.messages
        return []


class AvailableExamDetailView(APIView):
    def get(self, request, exam_id):
        student_code = str(request.query_params.get("student_code", "")).strip().upper()
        if not student_code:
            return Response(
                {"error": "student_code_required", "message": "Enter your student code first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        student = get_object_or_404(Student.objects.only("student_code", "level_id"), student_code=student_code)
        current_time = timezone.now()
        exam = get_object_or_404(
            Exam.objects.filter(
                id=exam_id,
                status="open",
                level_id=student.level_id,
            ).filter(
                models.Q(opens_at__isnull=True) | models.Q(opens_at__lte=current_time),
                models.Q(closes_at__isnull=True) | models.Q(closes_at__gte=current_time),
            ).select_related("level").prefetch_related("source_allocations__source__questions__choices")
        )
        try:
            exam.validate_generation()
        except ValidationError:
            return Response(
                {"error": "question_bank_incomplete", "message": "This exam is not ready yet."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(AvailableExamDetailSerializer(exam).data)


def admin_error(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return Response({"message": "Administrator access required."}, status=status.HTTP_403_FORBIDDEN)
    return None


class AdminLoginView(APIView):
    def post(self, request):
        user = authenticate(request, username=request.data.get("username", ""), password=request.data.get("password", ""))
        if not user or not user.is_active or not user.is_staff:
            return Response({"message": "Invalid administrator credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        return Response({"username": user.get_username()})


class AdminLogoutView(APIView):
    def post(self, request):
        if (error := admin_error(request)):
            return error
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminSessionView(APIView):
    def get(self, request):
        if (error := admin_error(request)):
            return error
        return Response({"username": request.user.get_username()})


class AdminExamGeneratorDataView(APIView):
    def get(self, request):
        if (error := admin_error(request)):
            return error
        levels = []
        for level in Level.objects.filter(is_active=True).prefetch_related("question_sources__subject"):
            levels.append({
                "id": level.id,
                "name": level.name,
                "sources": [{
                    "id": source.id,
                    "subject": source.subject.name,
                    "filename": source.original_filename,
                    "available_questions": source.question_count,
                } for source in level.question_sources.filter(is_active=True)]
            })
        return Response({"levels": levels})


class AdminExamGeneratorView(APIView):
    def post(self, request):
        if (error := admin_error(request)):
            return error
        try:
            level = Level.objects.get(id=request.data.get("level_id"), is_active=True)
            allocations = self.parse_allocations(level, request.data.get("allocations", []))
            configuration = {
                "level": level,
                "name": str(request.data.get("name", "")).strip(),
                "max_score": Decimal(str(request.data.get("max_score"))),
                "question_count": int(request.data.get("question_count")),
                "exam_date": date.fromisoformat(request.data.get("exam_date")),
                "time_limit_minutes": request.data.get("time_limit_minutes") or None,
                "opens_at": parse_datetime(request.data["opens_at"]) if request.data.get("opens_at") else None,
                "closes_at": parse_datetime(request.data["closes_at"]) if request.data.get("closes_at") else None,
                "allocations": allocations,
            }
            if not configuration["name"]:
                raise ValueError("Exam name is required.")
            with transaction.atomic():
                exam = create_exam(configuration)
        except (Level.DoesNotExist, QuestionSource.DoesNotExist, ValueError, InvalidOperation, TypeError, ValidationError) as error:
            message = error.messages[0] if isinstance(error, ValidationError) else str(error)
            return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serialize_exam(exam), status=status.HTTP_201_CREATED)

    @staticmethod
    def parse_allocations(level, payload):
        if not payload:
            raise ValueError("Add at least one question-source allocation.")
        allocations = []
        for item in payload:
            source = QuestionSource.objects.get(id=item.get("source_id"), level=level, is_active=True)
            allocations.append({"source": source, "question_count": int(item.get("question_count"))})
        return allocations

    @staticmethod
    def serialize_exam(exam):
        return {
            "id": exam.id,
            "name": exam.name,
            "status": exam.status,
            "question_count": exam.question_count,
            "max_score": str(exam.max_score),
            "points_per_question": str(exam.max_score / exam.question_count),
        }


class AdminExamPreviewView(APIView):
    def get(self, request, exam_id):
        if (error := admin_error(request)):
            return error
        exam = get_object_or_404(Exam, id=exam_id)
        return Response({"exam": AdminExamGeneratorView.serialize_exam(exam), "questions": preview_exam_questions(exam)})


class AdminExamStatusView(APIView):
    def post(self, request, exam_id):
        if (error := admin_error(request)):
            return error
        exam = get_object_or_404(Exam, id=exam_id)
        next_status = request.data.get("status")
        if next_status not in {"open", "closed"}:
            return Response({"message": "Status must be open or closed."}, status=status.HTTP_400_BAD_REQUEST)
        exam.status = next_status
        if next_status == "open":
            try:
                exam.full_clean()
            except ValidationError as error:
                return Response({"message": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        exam.save(update_fields=("status",))
        return Response(AdminExamGeneratorView.serialize_exam(exam))
