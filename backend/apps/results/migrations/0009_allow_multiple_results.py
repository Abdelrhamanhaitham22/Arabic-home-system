from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("results", "0008_alter_result_max_score_alter_result_score"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE results_result DROP CONSTRAINT IF EXISTS unique_result_per_student_exam;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
