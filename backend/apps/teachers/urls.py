from django.urls import path

from .views import (
    TeacherCsrfView,
    TeacherLoginView,
    TeacherLogoutView,
    TeacherMeView,
    TeacherSignupView,
)


urlpatterns = [
    path("csrf/", TeacherCsrfView.as_view(), name="teacher-csrf"),
    path("signup/", TeacherSignupView.as_view(), name="teacher-signup"),
    path("login/", TeacherLoginView.as_view(), name="teacher-login"),
    path("logout/", TeacherLogoutView.as_view(), name="teacher-logout"),
    path("me/", TeacherMeView.as_view(), name="teacher-me"),
]
