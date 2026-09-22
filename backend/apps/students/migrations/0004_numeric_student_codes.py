import secrets

from django.core.validators import RegexValidator
from django.db import migrations, models


CODE_LENGTH = 8
CODE_MAX = 10 ** CODE_LENGTH


def replace_student_codes(apps, schema_editor):
    Student = apps.get_model("students", "Student")
    used_codes = set(Student.objects.values_list("student_code", flat=True))
    new_codes = []

    for student in Student.objects.all().iterator():
        while True:
            code = f"{secrets.randbelow(CODE_MAX):0{CODE_LENGTH}d}"
            if code not in used_codes:
                used_codes.add(code)
                break
        new_codes.append((student.pk, code))

    for student_id, code in new_codes:
        Student.objects.filter(pk=student_id).update(student_code=code)


class Migration(migrations.Migration):
    dependencies = [("students", "0003_unique_passport_number")]

    operations = [
        migrations.RunPython(replace_student_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="student",
            name="student_code",
            field=models.CharField(
                db_index=True,
                editable=False,
                max_length=8,
                unique=True,
                validators=[
                    RegexValidator(r"^\d{8}$", "Student code must contain exactly 8 digits.")
                ],
            ),
        ),
    ]
