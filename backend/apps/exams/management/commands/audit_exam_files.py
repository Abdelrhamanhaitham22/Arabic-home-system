from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from apps.core.file_validation import validate_pdf_file
from apps.exams.models import Exam


class Command(BaseCommand):
    help = "Report exam records whose stored files are missing or are not valid PDFs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-issues",
            action="store_true",
            help="Exit with status 1 when an invalid or missing file is found.",
        )

    def handle(self, *args, **options):
        issues = 0
        for exam in Exam.objects.exclude(exam_file="").iterator():
            exam_label = str(exam.name).encode("ascii", "backslashreplace").decode("ascii")
            try:
                with exam.exam_file.open("rb") as uploaded_file:
                    validate_pdf_file(uploaded_file)
            except (FileNotFoundError, OSError) as error:
                issues += 1
                error_label = str(error).encode("ascii", "backslashreplace").decode("ascii")
                self.stdout.write(self.style.ERROR(f"{exam.id}: {exam_label}: {error_label}"))
            except ValidationError as error:
                issues += 1
                error_label = str(error).encode("ascii", "backslashreplace").decode("ascii")
                self.stdout.write(
                    self.style.ERROR(f"{exam.id}: {exam_label}: invalid PDF ({error_label})")
                )

        if issues:
            self.stdout.write(self.style.WARNING(f"Found {issues} exam file issue(s)."))
            if options["fail_on_issues"]:
                raise SystemExit(1)
        else:
            self.stdout.write(self.style.SUCCESS("All stored exam files are valid PDFs."))
