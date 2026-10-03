from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models


MAX_VIDEO_SIZE = 100 * 1024 * 1024
SUPPORTED_VIDEO_EXTENSIONS = ("mp4", "webm", "ogg")


def validate_video_size(uploaded_file):
    if uploaded_file.size > MAX_VIDEO_SIZE:
        raise ValidationError("Video files must be 100 MB or smaller.")


class HomepageVideo(models.Model):
    title_ar = models.CharField(max_length=200)
    title_ru = models.CharField(max_length=200)
    description_ar = models.TextField(blank=True)
    description_ru = models.TextField(blank=True)
    video = models.FileField(
        upload_to="homepage/videos/",
        validators=[
            FileExtensionValidator(allowed_extensions=SUPPORTED_VIDEO_EXTENSIONS),
            validate_video_size,
        ],
    )
    order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "created_at")
        verbose_name = "Homepage video"
        verbose_name_plural = "Homepage videos"

    def clean(self):
        super().clean()
        if self.video and Path(self.video.name).suffix.lower().lstrip(".") not in SUPPORTED_VIDEO_EXTENSIONS:
            raise ValidationError({"video": "Upload an MP4, WebM, or OGG video."})

    def __str__(self):
        return self.title_ar


class StaffProfile(models.Model):
    ROLE_CHOICES = [
        ("administrator", "Administrator"),
        ("editor", "Editor"),
        ("viewer", "Viewer"),
    ]

    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, related_name="staff_profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_username()} ({self.get_role_display()})"


class AuditLog(models.Model):
    actor = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.action} - {self.target_type} {self.target_id}"
