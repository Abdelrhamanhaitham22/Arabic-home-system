from django.core.exceptions import ValidationError
from django.db import models

from apps.exams.models import Exam
from apps.students.models import Student


class Result(models.Model):
    SUBMISSION_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("submitted", "Submitted"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="results")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="results")
    attempt = models.OneToOneField(
        "attempts.ExamAttempt", on_delete=models.SET_NULL, null=True, blank=True, related_name="result"
    )
    score = models.PositiveIntegerField()
    max_score = models.PositiveIntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    submission_status = models.CharField(max_length=20, choices=SUBMISSION_STATUS_CHOICES, default="pending")
    published = models.BooleanField(default=False)
    teacher_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("student", "exam"),
                name="unique_result_per_student_exam",
            )
        ]

    def clean(self):
        if self.exam_id and self.score > (self.max_score or self.exam.max_score):
            raise ValidationError({"score": "Score cannot exceed the exam maximum."})

    @property
    def is_complete(self):
        return self.submission_status == "submitted"

    def publish(self):
        self.max_score = self.max_score or self.exam.max_score
        self.percentage = round((self.score / self.max_score) * 100, 2) if self.max_score else 0
        self.full_clean()
        self.published = True
        self.save(update_fields=("score", "max_score", "percentage", "published", "updated_at"))

    def __str__(self):
        return f"{self.student.student_code} - {self.exam.name}"
