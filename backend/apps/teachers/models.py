from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal


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


class TeacherAssessmentConfig(models.Model):
    level = models.OneToOneField("exams.Level", on_delete=models.CASCADE, related_name="teacher_assessment_config")
    written_max = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("75"), validators=[MinValueValidator(Decimal("0"))])
    activity_dictation_max = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("50"), validators=[MinValueValidator(Decimal("0"))])
    oral_max = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("75"), validators=[MinValueValidator(Decimal("0"))])
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_max(self):
        return self.written_max + self.activity_dictation_max + self.oral_max


class TeacherAssessment(models.Model):
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="teacher_assessments")
    level = models.ForeignKey("exams.Level", on_delete=models.CASCADE, related_name="teacher_assessments")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="teacher_assessments")
    written_score = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    activity_dictation_score = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    oral_score = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    teacher_notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("student", "level"), name="unique_teacher_assessment_student_level")]

    @property
    def total_score(self):
        return self.written_score + self.activity_dictation_score + self.oral_score
