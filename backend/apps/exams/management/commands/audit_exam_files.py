from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Confirm that the legacy PDF exam workflow has been removed."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Legacy PDF exam files were removed in Phase 1."))
