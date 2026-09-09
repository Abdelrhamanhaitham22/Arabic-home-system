from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.students.models import Student

from .serializers import ResultLookupSerializer


@method_decorator(ratelimit(key="ip", rate="60/h", method="GET", block=True), name="dispatch")
class ResultLookupView(APIView):
    def get(self, request, student_code):
        try:
            student = Student.objects.prefetch_related("results__exam").get(
                student_code=student_code
            )
        except Student.DoesNotExist:
            return Response(
                {
                    "error": "student_not_found",
                    "message": _("Student number was not found. Please try again."),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        response_data = ResultLookupSerializer(student).data
        if not student.results.exists():
            response_data["message"] = _(
                "Your result has not been published yet. Please try again later."
            )
        return Response(response_data)
