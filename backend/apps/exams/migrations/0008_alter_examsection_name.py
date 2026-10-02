from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("exams", "0007_level_question_bank"),
    ]

    operations = [
        migrations.AlterField(
            model_name="examsection",
            name="name",
            field=models.CharField(default="Questions", max_length=100),
        ),
    ]
