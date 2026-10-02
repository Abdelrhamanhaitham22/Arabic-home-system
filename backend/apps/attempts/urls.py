from django.urls import path

from .views import AnswerView, AttemptDetailView, StartExamView, SubmitAttemptView


urlpatterns = [
    path("exams/<int:exam_id>/start/", StartExamView.as_view(), name="start-exam"),
    path("exam-attempts/<int:attempt_id>/", AttemptDetailView.as_view(), name="exam-attempt-detail"),
    path("exam-attempts/<int:attempt_id>/answers/", AnswerView.as_view(), name="exam-attempt-answers"),
    path("exam-attempts/<int:attempt_id>/submit/", SubmitAttemptView.as_view(), name="submit-exam-attempt"),
]
