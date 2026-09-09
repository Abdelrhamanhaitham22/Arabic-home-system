import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Exam",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("max_score", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("exam_date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
