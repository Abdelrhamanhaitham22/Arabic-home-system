from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("results", "0008_alter_result_max_score_alter_result_score"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="result",
            name="unique_result_per_student_exam",
        ),
    ]
