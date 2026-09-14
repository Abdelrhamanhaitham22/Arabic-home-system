from django.urls import path

from .views import ExamSubmissionFileView, ResultLookupView


urlpatterns = [
    path("submissions/<int:submission_id>/file/", ExamSubmissionFileView.as_view(), name="submission-file"),
    path("<str:student_code>/", ResultLookupView.as_view(), name="result-lookup"),
]
