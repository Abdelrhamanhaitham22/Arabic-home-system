import datetime

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.exams.models import Exam, ExamSection, Level


SECTIONS = (
    ("Reading", 15),
    ("Vocabulary", 15),
    ("Grammar", 15),
    ("Writing", 15),
    ("Listening", 10),
    ("Dictation", 10),
)
MAX_SCORE = sum(max_score for _, max_score in SECTIONS)


class Command(BaseCommand):
    help = "Create the Level 6 final exam and its scoring sections."

    def add_arguments(self, parser):
        parser.add_argument(
            "--exam-date",
            default=datetime.date.today().isoformat(),
            help="Exam date in YYYY-MM-DD format.",
        )
        parser.add_argument("--open", action="store_true", help="Open the exam after seeding it.")

    def handle(self, *args, **options):
        exam_date = datetime.date.fromisoformat(options["exam_date"])
        with transaction.atomic():
            level, _ = Level.objects.get_or_create(name="Level 6", defaults={"order": 6})
            exam, created = Exam.objects.get_or_create(
                name="Level 6 Final Exam",
                defaults={
                    "level": level,
                    "max_score": MAX_SCORE,
                    "exam_date": exam_date,
                    "status": "draft",
                },
            )
            changed_fields = []
            if exam.level_id != level.id:
                exam.level = level
                changed_fields.append("level")
            if exam.max_score != MAX_SCORE:
                exam.max_score = MAX_SCORE
                changed_fields.append("max_score")
            if exam.exam_date != exam_date:
                exam.exam_date = exam_date
                changed_fields.append("exam_date")
            if options["open"] and exam.status != "open":
                try:
                    level.validate_question_bank()
                except ValidationError as error:
                    raise CommandError(
                        "The exam cannot be opened until the level question bank is complete: "
                        + "; ".join(error.message_dict["question_bank"])
                    ) from error
                exam.status = "open"
                changed_fields.append("status")
            if changed_fields:
                exam.save(update_fields=changed_fields)

            section_names = [name for name, _ in SECTIONS]
            ExamSection.objects.filter(exam=exam).exclude(name__in=section_names).delete()
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
        self.stdout.write(self.style.SUCCESS(f"{action} {exam.name} with {len(SECTIONS)} sections ({MAX_SCORE} points)."))
