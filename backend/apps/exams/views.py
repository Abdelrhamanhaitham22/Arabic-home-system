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
from .generator import create_exam, preview_exam_questions, update_exam
from .models import Exam, Level, QuestionSource
from apps.core.services import has_staff_role, record_audit, staff_role
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
    if not request.user.is_authenticated or not has_staff_role(request.user, "viewer"):
        return Response({"message": "Staff access required."}, status=status.HTTP_403_FORBIDDEN)
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
        return Response({"username": request.user.get_username(), "role": staff_role(request.user), "is_superuser": request.user.is_superuser})


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
        if not has_staff_role(request.user, "editor"):
            return Response({"message": "Editor access required."}, status=status.HTTP_403_FORBIDDEN)
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
                record_audit(request.user, "exam.created", "Exam", exam.id, {"name": exam.name, "question_count": exam.question_count})
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


class AdminExamManagementView(APIView):
    def get(self, request):
        if (error := admin_error(request)):
            return error
        exams = Exam.objects.select_related("level").order_by("-created_at")
        return Response([self.serialize_exam(exam) for exam in exams])

    def post(self, request):
        if (error := admin_error(request)):
            return error
        if not has_staff_role(request.user, "editor"):
            return Response({"message": "Editor access required."}, status=status.HTTP_403_FORBIDDEN)
        source_exam = get_object_or_404(Exam, id=request.data.get("exam_id"))
        if source_exam.level_id is None:
            return Response({"message": "The source exam must have a level."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            configuration = management_configuration(source_exam, request.data)
            duplicate = create_exam(configuration)
            duplicate.name = f"{source_exam.name} copy"
            duplicate.save(update_fields=("name",))
            record_audit(request.user, "exam.duplicated", "Exam", duplicate.id, {"source_exam": source_exam.id})
        except (ValueError, InvalidOperation, TypeError, ValidationError) as error:
            message = error.messages[0] if isinstance(error, ValidationError) else str(error)
            return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serialize_exam(duplicate), status=status.HTTP_201_CREATED)

    @staticmethod
    def serialize_exam(exam):
        return {
            "id": exam.id,
            "name": exam.name,
            "level": exam.level.name if exam.level_id else None,
            "status": exam.status,
            "question_count": exam.question_count,
            "max_score": str(exam.max_score),
            "has_attempts": exam.attempts.exists(),
            "created_at": exam.created_at,
        }


class AdminExamEditView(APIView):
    def patch(self, request, exam_id):
        if (error := admin_error(request)):
            return error
        if not has_staff_role(request.user, "editor"):
            return Response({"message": "Editor access required."}, status=status.HTTP_403_FORBIDDEN)
        exam = get_object_or_404(Exam, id=exam_id)
        if exam.status != "draft" or exam.attempts.exists():
            return Response({"message": "Only untouched draft exams can be edited."}, status=status.HTTP_409_CONFLICT)
        try:
            configuration = management_configuration(exam, request.data)
            update_exam(exam, configuration)
        except (ValueError, InvalidOperation, TypeError, ValidationError) as error:
            message = error.messages[0] if isinstance(error, ValidationError) else str(error)
            return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)
        record_audit(request.user, "exam.updated", "Exam", exam.id, {"name": exam.name})
        return Response(AdminExamManagementView.serialize_exam(exam))


def management_configuration(exam, payload):
    allocations = []
    for allocation in exam.source_allocations.select_related("source"):
        allocation_payload = payload.get("allocations", {})
        source_count = allocation_payload.get(str(allocation.source_id), allocation.question_count)
        allocations.append({"source": allocation.source, "question_count": int(source_count)})
    return {
        "level": exam.level,
        "name": str(payload.get("name", exam.name)).strip(),
        "max_score": Decimal(str(payload.get("max_score", exam.max_score))),
        "question_count": int(payload.get("question_count", exam.question_count)),
        "exam_date": date.fromisoformat(payload.get("exam_date", str(exam.exam_date))),
        "time_limit_minutes": payload.get("time_limit_minutes", exam.time_limit_minutes) or None,
        "opens_at": parse_datetime(payload["opens_at"]) if payload.get("opens_at") else exam.opens_at,
        "closes_at": parse_datetime(payload["closes_at"]) if payload.get("closes_at") else exam.closes_at,
        "allocations": allocations,
    }


class AdminExamStatusView(APIView):
    def post(self, request, exam_id):
        if (error := admin_error(request)):
            return error
        if not has_staff_role(request.user, "editor"):
            return Response({"message": "Editor access required."}, status=status.HTTP_403_FORBIDDEN)
        exam = get_object_or_404(Exam, id=exam_id)
        if exam.attempts.exists():
            return Response({"message": "This exam is locked because student attempts have started."}, status=status.HTTP_409_CONFLICT)
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
        record_audit(request.user, "exam.status_changed", "Exam", exam.id, {"status": next_status})
        return Response(AdminExamGeneratorView.serialize_exam(exam))
