import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("attempts", "0003_allow_multiple_attempts"),
        ("exams", "0012_examquestion"),
        ("results", "0009_allow_multiple_results"),
        ("students", "0004_numeric_student_codes"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentPromotion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("written_score", models.DecimalField(decimal_places=2, max_digits=8)),
                ("activity_dictation_score", models.DecimalField(decimal_places=2, max_digits=8)),
                ("oral_score", models.DecimalField(decimal_places=2, max_digits=8)),
                ("total_score", models.DecimalField(decimal_places=2, max_digits=8)),
                ("total_max", models.DecimalField(decimal_places=2, max_digits=8)),
                ("percentage", models.DecimalField(decimal_places=2, max_digits=5)),
                ("promoted_at", models.DateTimeField(auto_now_add=True)),
                ("from_level", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="student_promotions_from", to="exams.level")),
                ("source_attempt", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="student_promotion", to="attempts.examattempt")),
                ("source_result", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="student_promotions", to="results.result")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="promotions", to="students.student")),
                ("to_level", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="student_promotions_to", to="exams.level")),
            ],
            options={
                "ordering": ("-promoted_at", "-id"),
            },
        ),
    ]
