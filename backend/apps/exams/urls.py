from django.urls import path

from .views import AvailableExamListView


urlpatterns = [
    path("", AvailableExamListView.as_view(), name="available-exams"),
]
