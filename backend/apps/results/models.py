from django.core.exceptions import ValidationError
from django.db import models

from apps.exams.models import Exam, ExamSection
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
        exam_section_ids = set(self.exam.sections.values_list("id", flat=True))
        if not exam_section_ids:
            return True
        scored_section_ids = set(
            self.section_scores.filter(section_id__in=exam_section_ids).values_list(
                "section_id", flat=True
            )
        )
        return scored_section_ids == exam_section_ids

    def publish(self):
        if not self.is_complete:
            raise ValidationError("All exam sections must be scored before publishing.")
        self.score = sum(
            section_score.score
            for section_score in self.section_scores.select_related("section").filter(
                section__exam_id=self.exam_id
            )
        )
        self.max_score = self.max_score or self.exam.max_score
        self.percentage = round((self.score / self.max_score) * 100, 2) if self.max_score else 0
        self.full_clean()
        self.published = True
        self.save(update_fields=("score", "max_score", "percentage", "published", "updated_at"))

    def __str__(self):
        return f"{self.student.student_code} - {self.exam.name}"


class SectionScore(models.Model):
    result = models.ForeignKey(Result, on_delete=models.CASCADE, related_name="section_scores")
    section = models.ForeignKey(ExamSection, on_delete=models.CASCADE, related_name="scores")
    score = models.PositiveIntegerField()
    teacher_comment = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("result", "section"),
                name="unique_result_section_score",
            )
        ]

    def clean(self):
        if self.section_id and self.score > self.section.max_score:
            raise ValidationError({"score": "Section score cannot exceed its maximum."})
        if self.result_id and self.section.exam_id != self.result.exam_id:
            raise ValidationError({"section": "Section must belong to the result exam."})
