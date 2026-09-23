from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.exams.models import Level

from .models import Student
from .serializers import LevelOptionSerializer, StudentLevelSerializer, StudentRegistrationSerializer


@method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True), name="dispatch")
class RegisterStudentView(APIView):
    def post(self, request):
        serializer = StudentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        return Response(
            {
                "message": _("Registration completed successfully."),
                "student_code": student.student_code,
                "full_name": student.full_name,
            },
            status=status.HTTP_201_CREATED,
        )


class StudentLevelOptionsView(APIView):
    def get(self, request):
        levels = (
            Level.objects.filter(is_active=True)
            .order_by("order", "name")
            .values("id", "name")
        )
        return Response(LevelOptionSerializer(levels, many=True).data)


@method_decorator(ratelimit(key="ip", rate="60/h", method="GET", block=True), name="dispatch")
class StudentLevelView(APIView):
    def get(self, request, student_code):
        student = get_object_or_404(
            Student.objects.select_related("level"),
            student_code=student_code.strip().upper(),
        )
        return Response(StudentLevelSerializer(student).data)
