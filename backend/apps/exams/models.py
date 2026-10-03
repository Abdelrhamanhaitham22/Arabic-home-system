from django.core.exceptions import ValidationError
from decimal import Decimal

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

    def question_bank_errors(self):
        active_questions = self.question_bank.filter(is_active=True).prefetch_related("choices")
        questions = list(active_questions)
        errors = []
        true_false_count = sum(question.question_type == "true_false" for question in questions)
        multiple_choice_count = sum(question.question_type == "multiple_choice" for question in questions)

        if not 100 <= len(questions) <= 300:
            errors.append("The active question bank must contain between 100 and 300 questions.")
        if true_false_count < 25:
            errors.append("The active question bank must contain at least 25 true/false questions.")
        if multiple_choice_count < 25:
            errors.append("The active question bank must contain at least 25 multiple-choice questions.")

        for question in questions:
            if question.question_type not in {"true_false", "multiple_choice"}:
                errors.append(f"Question {question.id} uses an unsupported question type.")
                continue
            choices = list(question.choices.all())
            if len(choices) < 2:
                errors.append(f"Question {question.id} must have at least two answer choices.")
            if sum(choice.is_correct for choice in choices) != 1:
                errors.append(f"Question {question.id} must have exactly one correct answer.")
        return errors

    def validate_question_bank(self):
        errors = self.question_bank_errors()
        if errors:
            raise ValidationError({"question_bank": errors})
        return True


class Subject(models.Model):
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=("level", "name"), name="unique_subject_name_per_level"),
        ]

    def __str__(self):
        return f"{self.level} - {self.name}"


class QuestionSource(models.Model):
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="question_sources")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="question_sources")
    file = models.FileField(upload_to="question-banks/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-uploaded_at", "id")

    def clean(self):
        if self.subject_id and self.level_id and self.subject.level_id != self.level_id:
            raise ValidationError({"subject": "The subject must belong to the selected level."})

    @property
    def question_count(self):
        return self.questions.filter(is_active=True).count()

    def __str__(self):
        return f"{self.level} - {self.subject.name} - {self.original_filename}"


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
    max_score = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    question_count = models.PositiveIntegerField(default=50, validators=[MinValueValidator(1)])
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
        if self.status == "open":
            if not self.level_id:
                raise ValidationError({"level": "An open exam must be assigned to a level."})
            self.validate_generation()

    def validate_generation(self):
        allocations = list(self.source_allocations.select_related("source"))
        if not allocations and self.pk:
            return True
        errors = []
        if not allocations:
            errors.append("Add at least one question-source allocation.")
        if sum(allocation.question_count for allocation in allocations) != self.question_count:
            errors.append("Allocated question counts must equal the exam question count.")
        for allocation in allocations:
            if allocation.source.level_id != self.level_id:
                errors.append("Every question source must belong to the exam level.")
            if allocation.question_count > allocation.source.question_count:
                errors.append(f"{allocation.source.original_filename} does not contain enough active questions.")
        if errors:
            raise ValidationError({"question_count": errors})
        return True

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


class ExamSourceAllocation(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="source_allocations")
    source = models.ForeignKey(QuestionSource, on_delete=models.PROTECT, related_name="exam_allocations")
    question_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ("source__subject__name", "source__original_filename")
        constraints = [
            models.UniqueConstraint(fields=("exam", "source"), name="unique_exam_question_source"),
        ]

    def clean(self):
        if self.exam_id and self.source_id and self.exam.level_id != self.source.level_id:
            raise ValidationError({"source": "The source file must belong to the exam level."})
        if self.question_count > self.source.question_count:
            raise ValidationError({"question_count": "The requested count exceeds the available questions."})

    def __str__(self):
        return f"{self.exam.name} - {self.source.original_filename}: {self.question_count}"


class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="selected_questions")
    question = models.ForeignKey("Question", on_delete=models.PROTECT, related_name="selected_for_exams")
    display_order = models.PositiveIntegerField()

    class Meta:
        ordering = ("display_order",)
        constraints = [
            models.UniqueConstraint(fields=("exam", "question"), name="unique_exam_selected_question"),
            models.UniqueConstraint(fields=("exam", "display_order"), name="unique_exam_selected_order"),
        ]

    def __str__(self):
        return f"{self.exam.name} - Question {self.display_order}"


class Question(models.Model):
    TYPE_CHOICES = [
        ("multiple_choice", "Multiple choice"),
        ("true_false", "True or false"),
        ("short_answer", "Short answer"),
        ("written", "Written answer"),
    ]

    level = models.ForeignKey(
        Level,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="question_bank",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    source = models.ForeignKey(
        QuestionSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    prompt = models.TextField()
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    points = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    order = models.PositiveIntegerField(default=0)
    bank_order = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    answer_text = models.TextField(blank=True)

    class Meta:
        ordering = ("bank_order", "order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("level", "bank_order"),
                condition=models.Q(level__isnull=False, bank_order__isnull=False),
                name="unique_level_question_bank_order",
            ),
        ]

    def clean(self):
        if self.subject_id and self.level_id and self.subject.level_id != self.level_id:
            raise ValidationError({"subject": "The subject must belong to the selected level."})
        if self.source_id and self.level_id and self.source.level_id != self.level_id:
            raise ValidationError({"source": "The source file must belong to the selected level."})
        if self.source_id and self.subject_id and self.source.subject_id != self.subject_id:
            raise ValidationError({"source": "The source file must belong to the selected subject."})
        if self.question_type in {"multiple_choice", "true_false"} and self.answer_text:
            raise ValidationError({"answer_text": "Objective questions use answer choices."})
        if self.is_active and self.question_type not in {"multiple_choice", "true_false"}:
            raise ValidationError({"question_type": "Active question banks support only objective questions."})

    def __str__(self):
        if self.level_id:
            return f"{self.level} - Question {self.bank_order or self.order}"
        return f"Question {self.order}"


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
