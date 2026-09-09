import datetime

from django.db import transaction


def generate_student_code() -> str:
    from .models import Student

    prefix = f"ST{datetime.date.today().year}"
    with transaction.atomic():
        latest_student = (
            Student.objects.select_for_update()
            .filter(student_code__startswith=prefix)
            .order_by("-student_code")
            .first()
        )
        next_sequence = int(latest_student.student_code[6:]) + 1 if latest_student else 1
        return f"{prefix}{next_sequence:05d}"
