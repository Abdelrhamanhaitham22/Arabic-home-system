from django.db import migrations


def publish_existing_results(apps, schema_editor):
    Result = apps.get_model("results", "Result")
    Result.objects.filter(published=False).update(published=True)


class Migration(migrations.Migration):
    dependencies = [
        ("results", "0002_result_published_result_teacher_notes_examsubmission_and_more"),
    ]

    operations = [
        migrations.RunPython(publish_existing_results, migrations.RunPython.noop),
    ]
