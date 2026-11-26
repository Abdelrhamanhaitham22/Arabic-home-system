from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.exams.models import Exam


class Command(BaseCommand):
    help = "Delete exams, attempts, and results while preserving question banks and promotion history."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm deletion of all exams, attempts, and results.",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError("Refusing to delete data without --confirm.")

        with transaction.atomic():
            deleted_exams, _ = Exam.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_exams} exam-related records. "
                "Question banks and student promotion history were preserved."
            )
        )
