from django.urls import path

from .views import RegisterStudentView, StudentLevelOptionsView, StudentLevelView


urlpatterns = [
    path("register/", RegisterStudentView.as_view(), name="student-register"),
    path("levels/", StudentLevelOptionsView.as_view(), name="student-level-options"),
    path("<str:student_code>/level/", StudentLevelView.as_view(), name="student-level"),
]
