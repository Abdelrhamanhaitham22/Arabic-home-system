import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0007_student_assigned_exam"),
    ]

    operations = [
        migrations.AlterField(
            model_name="studentpromotion",
            name="source_attempt",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="student_promotion",
                to="attempts.examattempt",
            ),
        ),
    ]
