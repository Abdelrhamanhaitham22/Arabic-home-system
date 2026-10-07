from django.urls import path

from .views import (
    TeacherCsrfView,
    TeacherLoginView,
    TeacherLogoutView,
    TeacherMeView,
    TeacherSignupView,
    TeacherAssessmentView,
    TeacherAssessmentConfigView,
)


urlpatterns = [
    path("csrf/", TeacherCsrfView.as_view(), name="teacher-csrf"),
    path("signup/", TeacherSignupView.as_view(), name="teacher-signup"),
    path("login/", TeacherLoginView.as_view(), name="teacher-login"),
    path("logout/", TeacherLogoutView.as_view(), name="teacher-logout"),
    path("me/", TeacherMeView.as_view(), name="teacher-me"),
    path("assessments/<str:student_code>/", TeacherAssessmentView.as_view(), name="teacher-assessment"),
    path("assessment-config/", TeacherAssessmentConfigView.as_view(), name="teacher-assessment-config"),
    path("assessment-config/<int:level_id>/", TeacherAssessmentConfigView.as_view(), name="teacher-assessment-config-level"),
]
