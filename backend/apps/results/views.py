from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.students.models import Student

from .models import ExamSubmission
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

        published_results = student.results.filter(published=True)
        response_data = ResultLookupSerializer(student, context={"published_results": published_results}).data
        if not published_results.exists():
            response_data["message"] = _(
                "Your result has not been published yet. Please try again later."
            )
        return Response(response_data)


class ExamSubmissionFileView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, submission_id):
        submission = get_object_or_404(ExamSubmission, id=submission_id)
        if not submission.answer_file:
            raise Http404
        try:
            answer_file = submission.answer_file.open("rb")
        except FileNotFoundError as error:
            raise Http404("The answer file is temporarily unavailable.") from error
        return FileResponse(answer_file, content_type="application/octet-stream")
