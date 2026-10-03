from django.urls import path

from .views import AuditLogView, StaffAccountView, homepage_videos


urlpatterns = [
    path("videos/", homepage_videos, name="homepage-videos"),
    path("staff/", StaffAccountView.as_view(), name="staff-accounts"),
    path("staff/<int:user_id>/", StaffAccountView.as_view(), name="staff-account"),
    path("audit-logs/", AuditLogView.as_view(), name="audit-logs"),
]
