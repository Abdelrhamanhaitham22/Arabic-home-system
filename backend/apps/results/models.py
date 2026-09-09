from django.core.exceptions import ValidationError
from django.db import models

from apps.exams.models import Exam
from apps.students.models import Student


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="results")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="results")
    score = models.PositiveIntegerField()
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
        if self.exam_id and self.score > self.exam.max_score:
            raise ValidationError({"score": "Score cannot exceed the exam maximum."})

    @property
    def percentage(self):
        if self.exam.max_score == 0:
            return 0
        return round((self.score / self.exam.max_score) * 100, 2)

    def __str__(self):
        return f"{self.student.student_code} - {self.exam.name}"
