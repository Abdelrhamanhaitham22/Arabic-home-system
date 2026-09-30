from django.core.exceptions import ValidationError
from django.db import models

from apps.exams.models import Exam, ExamSection
from apps.students.models import Student


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="results")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="results")
    score = models.PositiveIntegerField()
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
        if self.exam_id and self.score > self.exam.max_score:
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
        self.full_clean()
        self.published = True
        self.save(update_fields=("score", "published", "updated_at"))

    @property
    def percentage(self):
        if self.exam.max_score == 0:
            return 0
        return round((self.score / self.exam.max_score) * 100, 2)

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
