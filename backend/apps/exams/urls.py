from django.urls import path

from .views import AvailableExamDetailView, AvailableExamListView


urlpatterns = [
    path("", AvailableExamListView.as_view(), name="available-exams"),
    path("<int:exam_id>/", AvailableExamDetailView.as_view(), name="available-exam-detail"),
]
