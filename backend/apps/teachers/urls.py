from django.urls import path

from .views import (
    TeacherCsrfView,
    TeacherLoginView,
    TeacherLogoutView,
    TeacherMeView,
    TeacherSubmissionFileView,
    TeacherSubmissionGradeView,
)


urlpatterns = [
    path("csrf/", TeacherCsrfView.as_view(), name="teacher-csrf"),
    path("login/", TeacherLoginView.as_view(), name="teacher-login"),
    path("logout/", TeacherLogoutView.as_view(), name="teacher-logout"),
    path("me/", TeacherMeView.as_view(), name="teacher-me"),
    path("submissions/<int:submission_id>/file/", TeacherSubmissionFileView.as_view(), name="teacher-submission-file"),
    path("submissions/<int:submission_id>/grade/", TeacherSubmissionGradeView.as_view(), name="teacher-submission-grade"),
]
