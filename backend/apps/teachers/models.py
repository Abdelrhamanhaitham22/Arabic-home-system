from django.conf import settings
from django.db import models


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    levels = models.ManyToManyField("exams.Level", related_name="teachers", blank=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.user.get_username()
