from django.db import models

from .services import generate_student_code


class Student(models.Model):
    LANGUAGE_CHOICES = [("ar", "العربية"), ("ru", "Русский")]

    student_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        editable=False,
    )
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    passport_number = models.CharField(max_length=50)
    level = models.ForeignKey(
        "exams.Level",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    preferred_language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="ar",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.student_code:
            self.student_code = generate_student_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student_code} - {self.full_name}"
