from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


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
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.opens_at and self.closes_at and self.closes_at <= self.opens_at:
            raise ValidationError({"closes_at": "Closing time must be after opening time."})

    @property
    def is_submission_open(self):
        if self.status != "open":
            return False
        now = timezone.now()
        return (not self.opens_at or now >= self.opens_at) and (
            not self.closes_at or now <= self.closes_at
        )

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
