from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.students.models import Student
from apps.results.models import ExamSubmission

from .models import Exam
from .serializers import AvailableExamSerializer, ExamSubmissionSerializer


MAX_ANSWER_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_ANSWER_TYPES = {"application/pdf", "image/jpeg", "image/png"}


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
        exams = Exam.objects.filter(status="open", level_id=student.level_id).select_related(
            "level"
        ).prefetch_related("sections")
        return Response(AvailableExamSerializer(exams, many=True, context={"request": request}).data)


class ExamFileView(APIView):
    def get(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id, status="open")
        if not exam.exam_file:
            raise Http404
        try:
            exam_file = exam.exam_file.open("rb")
        except FileNotFoundError as error:
            raise Http404("The exam file is temporarily unavailable.") from error
        return FileResponse(exam_file, content_type="application/pdf")


class ExamSubmissionCreateView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        student_code = str(request.data.get("student_code", "")).strip().upper()
        student = get_object_or_404(Student, student_code=student_code)
        exam = get_object_or_404(Exam, id=request.data.get("exam"), status="open")
        if not student.level_id or exam.level_id != student.level_id:
            return Response(
                {"error": "exam_not_available_for_student_level"},
                status=status.HTTP_403_FORBIDDEN,
            )
        answer_file = request.FILES.get("answer_file")
        if not answer_file:
            return Response({"error": "answer_file_required"}, status=status.HTTP_400_BAD_REQUEST)
        if answer_file.size > MAX_ANSWER_FILE_SIZE:
            return Response({"error": "answer_file_too_large"}, status=status.HTTP_400_BAD_REQUEST)
        if answer_file.content_type not in ALLOWED_ANSWER_TYPES:
            return Response({"error": "unsupported_answer_file_type"}, status=status.HTTP_400_BAD_REQUEST)
        submission, created = ExamSubmission.objects.get_or_create(
            student=student,
            exam=exam,
            defaults={"answer_file": answer_file},
        )
        if not created:
            return Response({"error": "duplicate_submission"}, status=status.HTTP_409_CONFLICT)
        return Response(ExamSubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)
