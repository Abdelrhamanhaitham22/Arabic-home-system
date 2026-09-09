from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Student",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("student_code", models.CharField(db_index=True, editable=False, max_length=20, unique=True)),
                ("full_name", models.CharField(max_length=255)),
                ("phone_number", models.CharField(max_length=20)),
                ("address", models.TextField()),
                ("passport_number", models.CharField(max_length=50)),
                ("preferred_language", models.CharField(choices=[("ar", "العربية"), ("ru", "Русский")], default="ar", max_length=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
