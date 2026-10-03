from django.urls import path

from .views import (
    AdminExamGeneratorDataView,
    AdminExamGeneratorView,
    AdminExamPreviewView,
    AdminExamStatusView,
    AdminLoginView,
    AdminLogoutView,
    AdminSessionView,
    AvailableExamDetailView,
    AvailableExamListView,
)


urlpatterns = [
    path("admin-session/login/", AdminLoginView.as_view(), name="admin-login"),
    path("admin-session/logout/", AdminLogoutView.as_view(), name="admin-logout"),
    path("admin-session/me/", AdminSessionView.as_view(), name="admin-session"),
    path("admin-generator/data/", AdminExamGeneratorDataView.as_view(), name="admin-exam-generator-data"),
    path("admin-generator/exams/", AdminExamGeneratorView.as_view(), name="admin-exam-generator-create"),
    path("admin-generator/exams/<int:exam_id>/preview/", AdminExamPreviewView.as_view(), name="admin-exam-generator-preview"),
    path("admin-generator/exams/<int:exam_id>/status/", AdminExamStatusView.as_view(), name="admin-exam-generator-status"),
    path("", AvailableExamListView.as_view(), name="available-exams"),
    path("<int:exam_id>/", AvailableExamDetailView.as_view(), name="available-exam-detail"),
]
