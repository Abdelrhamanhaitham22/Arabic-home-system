from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("exams", "0002_level_exam_exam_file_exam_status_exam_level_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TeacherProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_profile", to=settings.AUTH_USER_MODEL)),
                ("levels", models.ManyToManyField(blank=True, related_name="teachers", to="exams.level")),
            ],
        ),
    ]
