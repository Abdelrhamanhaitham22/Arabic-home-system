from django.db import migrations


def delete_legacy_exam_records_and_files(apps, schema_editor):
    exam_model = apps.get_model("exams", "Exam")
    for exam in exam_model.objects.exclude(exam_file="").iterator():
        if exam.exam_file:
            exam.exam_file.delete(save=False)
    exam_model.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("exams", "0004_alter_exam_exam_file"),
        ("results", "0005_remove_legacy_submissions"),
    ]

    operations = [
        migrations.RunPython(delete_legacy_exam_records_and_files, migrations.RunPython.noop),
        migrations.RemoveField(model_name="exam", name="exam_file"),
    ]
