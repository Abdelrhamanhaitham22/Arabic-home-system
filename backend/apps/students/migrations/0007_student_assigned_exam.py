from django.db import migrations, models
import django.db.models.deletion


def assign_existing_students(apps, schema_editor):
    Student = apps.get_model("students", "Student")
    StudentPromotion = apps.get_model("students", "StudentPromotion")
    Exam = apps.get_model("exams", "Exam")
    promoted_ids = set(StudentPromotion.objects.values_list("student_id", flat=True))
    for student in Student.objects.exclude(level_id=None).iterator():
        if student.id in promoted_ids:
            continue
        open_exams = list(Exam.objects.filter(level_id=student.level_id, status="open").values_list("id", flat=True)[:2])
        if len(open_exams) == 1:
            Student.objects.filter(pk=student.pk).update(assigned_exam_id=open_exams[0])


class Migration(migrations.Migration):
    dependencies = [
        ("students", "0006_studentpromotionroster"),
        ("exams", "0012_examquestion"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="assigned_exam",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_students",
                to="exams.exam",
            ),
        ),
        migrations.RunPython(assign_existing_students, migrations.RunPython.noop),
    ]
