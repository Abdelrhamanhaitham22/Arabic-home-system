from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("exams", "0002_level_exam_exam_file_exam_status_exam_level_and_more")]

    operations = [
        migrations.AddField(
            model_name="exam",
            name="closes_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="exam",
            name="opens_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
