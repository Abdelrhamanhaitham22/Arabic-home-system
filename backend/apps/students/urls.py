from django.urls import path

from .views import RegisterStudentView, StudentLevelView


urlpatterns = [
    path("register/", RegisterStudentView.as_view(), name="student-register"),
    path("<str:student_code>/level/", StudentLevelView.as_view(), name="student-level"),
]
