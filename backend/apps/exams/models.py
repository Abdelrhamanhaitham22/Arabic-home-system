from django.core.validators import MinValueValidator
from django.db import models


class Level(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField(unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("order",)

    def __str__(self):
        return self.name


class Exam(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("open", "Open for submissions"),
        ("closed", "Closed"),
    ]

    level = models.ForeignKey(
        Level,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams",
    )
    name = models.CharField(max_length=255)
    max_score = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    exam_date = models.DateField()
    exam_file = models.FileField(upload_to="exams/", blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.exam_date})"


class ExamSection(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=100)
    max_score = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ("order",)
        constraints = [
            models.UniqueConstraint(
                fields=("exam", "order"),
                name="unique_exam_section_order",
            ),
            models.UniqueConstraint(
                fields=("exam", "name"),
                name="unique_exam_section_name",
            ),
        ]

    def __str__(self):
        return f"{self.exam.name} - {self.name}"
