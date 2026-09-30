from django.db import migrations


def delete_legacy_submission_files(apps, schema_editor):
    submission_model = apps.get_model("results", "ExamSubmission")
    for submission in submission_model.objects.exclude(answer_file="").iterator():
        if submission.answer_file:
            submission.answer_file.delete(save=False)


class Migration(migrations.Migration):
    dependencies = [
        ("exams", "0004_alter_exam_exam_file"),
        ("results", "0004_alter_examsubmission_answer_file"),
    ]

    operations = [
        migrations.RunPython(delete_legacy_submission_files, migrations.RunPython.noop),
        migrations.RemoveField(model_name="result", name="submission"),
        migrations.DeleteModel(name="ExamSubmission"),
    ]
