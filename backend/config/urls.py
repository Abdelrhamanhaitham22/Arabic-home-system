from django.contrib import admin
from django.urls import include, path
from apps.core.views import health_check


urlpatterns = [
    path("health/", health_check),
    path("admin/", admin.site.urls),
    path("api/students/", include("apps.students.urls")),
    path("api/results/", include("apps.results.urls")),
]
