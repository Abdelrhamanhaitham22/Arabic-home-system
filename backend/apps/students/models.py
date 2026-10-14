from django.db import models
from django.core.validators import RegexValidator

from .services import generate_student_code


class Student(models.Model):
    LANGUAGE_CHOICES = [("ar", "العربية"), ("ru", "Русский")]

    student_code = models.CharField(
        max_length=8,
        unique=True,
        db_index=True,
        editable=False,
        validators=[RegexValidator(r"^\d{8}$", "Student code must contain exactly 8 digits.")],
    )
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    passport_number = models.CharField(max_length=50, unique=True)
    level = models.ForeignKey(
        "exams.Level",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    preferred_language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="ar",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.student_code:
            self.student_code = generate_student_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student_code} - {self.full_name}"


class StudentPromotionRoster(Student):
    class Meta:
        proxy = True
        verbose_name = "Student promotion roster"
        verbose_name_plural = "Student promotion roster"


class StudentPromotion(models.Model):
    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="promotions")
    source_attempt = models.OneToOneField(
        "attempts.ExamAttempt",
        on_delete=models.PROTECT,
        related_name="student_promotion",
    )
    source_result = models.ForeignKey(
        "results.Result",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_promotions",
    )
    from_level = models.ForeignKey(
        "exams.Level",
        on_delete=models.PROTECT,
        related_name="student_promotions_from",
    )
    to_level = models.ForeignKey(
        "exams.Level",
        on_delete=models.PROTECT,
        related_name="student_promotions_to",
    )
    written_score = models.DecimalField(max_digits=8, decimal_places=2)
    activity_dictation_score = models.DecimalField(max_digits=8, decimal_places=2)
    oral_score = models.DecimalField(max_digits=8, decimal_places=2)
    total_score = models.DecimalField(max_digits=8, decimal_places=2)
    total_max = models.DecimalField(max_digits=8, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    promoted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-promoted_at", "-id")

    def __str__(self):
        return f"{self.student.student_code}: {self.from_level} to {self.to_level}"
