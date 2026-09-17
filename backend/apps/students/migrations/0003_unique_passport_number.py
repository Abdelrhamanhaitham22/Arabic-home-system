from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0002_student_level"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="passport_number",
            field=models.CharField(max_length=50, unique=True),
        ),
    ]
