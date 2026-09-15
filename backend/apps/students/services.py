import secrets


STUDENT_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
STUDENT_CODE_RANDOM_LENGTH = 12


def generate_student_code() -> str:
    from .models import Student

    while True:
        random_part = "".join(
            secrets.choice(STUDENT_CODE_ALPHABET)
            for _ in range(STUDENT_CODE_RANDOM_LENGTH)
        )
        code = f"ST-{random_part}"
        if not Student.objects.filter(student_code=code).exists():
            return code
