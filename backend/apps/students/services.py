import secrets


STUDENT_CODE_LENGTH = 8
STUDENT_CODE_MAX = 10 ** STUDENT_CODE_LENGTH


def generate_student_code() -> str:
    from .models import Student

    while True:
        code = f"{secrets.randbelow(STUDENT_CODE_MAX):0{STUDENT_CODE_LENGTH}d}"
        if not Student.objects.filter(student_code=code).exists():
            return code
