from django.urls import path

from .views import AvailableExamListView, ExamFileView, ExamSubmissionCreateView


urlpatterns = [
    path("", AvailableExamListView.as_view(), name="available-exams"),
    path("<int:exam_id>/file/", ExamFileView.as_view(), name="exam-file"),
    path("submissions/", ExamSubmissionCreateView.as_view(), name="exam-submission-create"),
]
