from django.contrib import admin
from django.urls import include, path
from apps.core.views import health_check


urlpatterns = [
    path("", health_check, name="root-health"),
    path("health/", health_check),
    path("admin/", admin.site.urls),
    path("api/students/", include("apps.students.urls")),
    path("api/exams/", include("apps.exams.urls")),
    path("api/results/", include("apps.results.urls")),
    path("api/teachers/", include("apps.teachers.urls")),
]
