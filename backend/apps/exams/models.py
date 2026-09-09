from django.core.validators import MinValueValidator
from django.db import models


class Exam(models.Model):
    name = models.CharField(max_length=255)
    max_score = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    exam_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.exam_date})"
