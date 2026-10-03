from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class ExamAttempt(models.Model):
    STATUS_CHOICES = [("in_progress", "In progress"), ("submitted", "Submitted")]

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="exam_attempts")
    exam = models.ForeignKey("exams.Exam", on_delete=models.CASCADE, related_name="attempts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("student", "exam"), name="unique_attempt_per_student_exam"),
        ]
        ordering = ("-started_at",)

    def clean(self):
        if self.status == "submitted" and not self.submitted_at:
            raise ValidationError({"submitted_at": "Submitted attempts require a submission time."})
        if self.max_score and self.score > self.max_score:
            raise ValidationError({"score": "Score cannot exceed the attempt maximum."})

    @property
    def deadline(self):
        if self.exam.time_limit_minutes is None:
            return None
        from datetime import timedelta

        return self.started_at + timedelta(minutes=self.exam.time_limit_minutes)

    @property
    def is_expired(self):
        from django.utils import timezone

        return self.deadline is not None and timezone.now() >= self.deadline

    def __str__(self):
        return f"{self.student.student_code} - {self.exam.name}"


class AttemptQuestion(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name="questions")
    original_question = models.ForeignKey(
        "exams.Question", on_delete=models.SET_NULL, null=True, blank=True, related_name="attempt_snapshots"
    )
    display_order = models.PositiveIntegerField()
    points_snapshot = models.DecimalField(max_digits=8, decimal_places=2)
    question_text_snapshot = models.TextField()
    question_type_snapshot = models.CharField(max_length=20)
    choices_snapshot = models.JSONField(default=list)
    correct_answer_snapshot = models.JSONField(default=dict)

    class Meta:
        ordering = ("display_order",)
        constraints = [
            models.UniqueConstraint(fields=("attempt", "original_question"), name="unique_attempt_original_question"),
            models.UniqueConstraint(fields=("attempt", "display_order"), name="unique_attempt_question_order"),
        ]

    def __str__(self):
        return f"Attempt {self.attempt_id} - Question {self.display_order}"


class StudentAnswer(models.Model):
    attempt_question = models.OneToOneField(AttemptQuestion, on_delete=models.CASCADE, related_name="answer")
    selected_choice = models.ForeignKey(
        "exams.QuestionChoice", on_delete=models.SET_NULL, null=True, blank=True, related_name="student_answers"
    )
    selected_answer_value = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    points_earned = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    answered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Answer for {self.attempt_question}"
