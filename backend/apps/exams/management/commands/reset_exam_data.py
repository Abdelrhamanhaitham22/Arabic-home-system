from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.attempts.models import ExamAttempt
from apps.exams.models import Exam, Question
from apps.results.models import Result


class Command(BaseCommand):
    help = "Delete exam content, attempts, and results while preserving students and levels."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm deletion of all exam content, attempts, and results.",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError("Refusing to delete data without --confirm.")

        with transaction.atomic():
            deleted_questions, _ = Question.objects.all().delete()
            deleted_attempts, _ = ExamAttempt.objects.all().delete()
            deleted_results, _ = Result.objects.all().delete()
            deleted_exams, _ = Exam.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_questions} question records, "
                f"{deleted_exams} exam records, {deleted_attempts} attempt records, "
                f"and {deleted_results} result records."
            )
        )
