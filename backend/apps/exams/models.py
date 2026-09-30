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
        ("published", "Published"),
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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.opens_at and self.closes_at and self.closes_at <= self.opens_at:
            raise ValidationError({"closes_at": "Closing time must be after opening time."})
        if self.status == "published" and not self.pk:
            raise ValidationError({"status": "Save the exam before publishing it."})

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


class Question(models.Model):
    TYPE_CHOICES = [
        ("multiple_choice", "Multiple choice"),
        ("true_false", "True or false"),
        ("short_answer", "Short answer"),
        ("written", "Written answer"),
    ]

    section = models.ForeignKey(ExamSection, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    points = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    order = models.PositiveIntegerField()
    answer_text = models.TextField(blank=True)

    class Meta:
        ordering = ("order",)
        constraints = [
            models.UniqueConstraint(
                fields=("section", "order"),
                name="unique_section_question_order",
            ),
        ]

    def clean(self):
        if self.question_type in {"multiple_choice", "true_false"} and self.answer_text:
            raise ValidationError({"answer_text": "Objective questions use answer choices."})

    def __str__(self):
        return f"{self.section} - Question {self.order}"


class QuestionChoice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=500)
    order = models.PositiveIntegerField()
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ("order",)
        constraints = [
            models.UniqueConstraint(
                fields=("question", "order"),
                name="unique_question_choice_order",
            ),
        ]

    def __str__(self):
        return f"{self.question} - Choice {self.order}"
