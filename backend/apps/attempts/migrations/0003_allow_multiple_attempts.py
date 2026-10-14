from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("attempts", "0002_alter_attemptquestion_points_snapshot_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="examattempt",
            name="unique_attempt_per_student_exam",
        ),
    ]
