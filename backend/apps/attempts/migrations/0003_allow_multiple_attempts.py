from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("attempts", "0002_alter_attemptquestion_points_snapshot_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE attempts_examattempt DROP CONSTRAINT IF EXISTS unique_attempt_per_student_exam;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
