from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.students.models import Student
from .models import Exam
from .serializers import AvailableExamSerializer


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
        ).select_related("level").prefetch_related("sections")
        return Response(AvailableExamSerializer(exams, many=True, context={"request": request}).data)
