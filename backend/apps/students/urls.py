from django.urls import path

from .views import RegisterStudentView, csrf_token, teacher_login, teacher_logout, teacher_session


urlpatterns = [
    path("csrf/", csrf_token, name="csrf-token"),
    path("login/", teacher_login, name="teacher-login"),
    path("logout/", teacher_logout, name="teacher-logout"),
    path("session/", teacher_session, name="teacher-session"),
    path("register/", RegisterStudentView.as_view(), name="student-register"),
]
