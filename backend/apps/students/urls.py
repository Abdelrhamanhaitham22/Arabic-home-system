from django.urls import path

from .views import RegisterStudentView


urlpatterns = [
    path("register/", RegisterStudentView.as_view(), name="student-register"),
]
