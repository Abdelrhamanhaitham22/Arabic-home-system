import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.files import File

from apps.exams.models import Exam, ExamSection, Level


SECTIONS = (
    ("Reading", 15),
    ("Vocabulary", 15),
    ("Grammar", 15),
    ("Writing", 15),
    ("Listening", 10),
    ("Dictation", 10),
    ("Activity", 40),
    ("Oral", 80),
)


class Command(BaseCommand):
    help = "Create the Level 6 final exam and its scoring sections."

    def add_arguments(self, parser):
        parser.add_argument(
            "--exam-date",
            default=datetime.date.today().isoformat(),
            help="Exam date in YYYY-MM-DD format.",
        )
        parser.add_argument(
            "--exam-file",
            help="Path to the Level 6 exam PDF to attach.",
        )

    def handle(self, *args, **options):
        exam_date = datetime.date.fromisoformat(options["exam_date"])
        level, _ = Level.objects.get_or_create(name="Level 6", defaults={"order": 6})
        exam, created = Exam.objects.get_or_create(
            name="Level 6 Final Exam",
            defaults={
                "level": level,
                "max_score": 200,
                "exam_date": exam_date,
                "status": "draft",
            },
        )
        if exam.level_id != level.id:
            exam.level = level
            exam.save(update_fields=("level",))
        if exam.max_score != 200:
            exam.max_score = 200
            exam.save(update_fields=("max_score",))

        exam_file_path = options.get("exam_file")
        if exam_file_path:
            path = Path(exam_file_path)
            if path.suffix.lower() != ".pdf":
                raise ValueError("The exam file must be a PDF.")
            with path.open("rb") as exam_file:
                exam.exam_file.save(path.name, File(exam_file), save=True)

        for order, (name, max_score) in enumerate(SECTIONS, start=1):
            section, created_section = ExamSection.objects.get_or_create(
                exam=exam,
                name=name,
                defaults={"max_score": max_score, "order": order},
            )
            if not created_section and (
                section.max_score != max_score or section.order != order
            ):
                section.max_score = max_score
                section.order = order
                section.save(update_fields=("max_score", "order"))

        action = "Created" if created else "Verified"
        self.stdout.write(self.style.SUCCESS(f"{action} {exam.name} with 8 sections (200 points)."))
