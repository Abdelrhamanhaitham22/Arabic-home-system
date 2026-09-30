from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.static import serve
from apps.core.views import health_check


urlpatterns = [
    path("", health_check, name="root-health"),
    path("health/", health_check),
    path("admin/", admin.site.urls),
    path("api/core/", include("apps.core.urls")),
    path("api/students/", include("apps.students.urls")),
    path("api/exams/", include("apps.exams.urls")),
    path("api/results/", include("apps.results.urls")),
    path("api/teachers/", include("apps.teachers.urls")),
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
