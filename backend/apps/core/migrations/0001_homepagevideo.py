from django.db import migrations, models
import django.core.validators
import apps.core.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="HomepageVideo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title_ar", models.CharField(max_length=200)),
                ("title_ru", models.CharField(max_length=200)),
                ("description_ar", models.TextField(blank=True)),
                ("description_ru", models.TextField(blank=True)),
                ("video", models.FileField(upload_to="homepage/videos/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=("mp4", "webm", "ogg")), apps.core.models.validate_video_size])),
                ("order", models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Homepage video",
                "verbose_name_plural": "Homepage videos",
                "ordering": ("order", "created_at"),
            },
        ),
    ]
