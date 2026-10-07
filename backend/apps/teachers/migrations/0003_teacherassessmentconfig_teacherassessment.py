from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("exams", "0012_examquestion"),
        ("students", "0004_numeric_student_codes"),
        ("teachers", "0002_teacherprofile_is_approved"),
    ]

    operations = [
        migrations.CreateModel(
            name="TeacherAssessmentConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("written_max", models.DecimalField(decimal_places=2, default=Decimal("75"), max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal("0"))])),
                ("activity_dictation_max", models.DecimalField(decimal_places=2, default=Decimal("50"), max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal("0"))])),
                ("oral_max", models.DecimalField(decimal_places=2, default=Decimal("75"), max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal("0"))])),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("level", models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="teacher_assessment_config", to="exams.level")),
            ],
        ),
        migrations.CreateModel(
            name="TeacherAssessment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("written_score", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=8)),
                ("activity_dictation_score", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=8)),
                ("oral_score", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=8)),
                ("teacher_notes", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("level", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="teacher_assessments", to="exams.level")),
                ("student", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="teacher_assessments", to="students.student")),
                ("teacher", models.ForeignKey(null=True, on_delete=models.deletion.SET_NULL, related_name="teacher_assessments", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="teacherassessment",
            constraint=models.UniqueConstraint(fields=("student", "level"), name="unique_teacher_assessment_student_level"),
        ),
    ]
