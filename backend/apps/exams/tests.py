import datetime
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import Exam, ExamSection, Level


class SeedLevel6ExamCommandTests(TestCase):
    def test_command_creates_level_exam_and_scoring_sections(self):
        output = StringIO()

        call_command("seed_level_6_exam", "--exam-date", "2026-09-14", stdout=output)

        level = Level.objects.get(name="Level 6")
        exam = Exam.objects.get(name="Level 6 Final Exam")
        sections = list(ExamSection.objects.filter(exam=exam))

        self.assertEqual(level.order, 6)
        self.assertEqual(exam.level, level)
        self.assertEqual(exam.exam_date, datetime.date(2026, 9, 14))
        self.assertEqual(exam.max_score, 80)
        self.assertEqual(
            [(section.name, section.max_score) for section in sections],
            [
                ("Reading", 15),
                ("Vocabulary", 15),
                ("Grammar", 15),
                ("Writing", 15),
                ("Listening", 10),
                ("Dictation", 10),
            ],
        )

    def test_command_is_idempotent(self):
        call_command("seed_level_6_exam", "--exam-date", "2026-09-14")
        call_command("seed_level_6_exam", "--exam-date", "2026-09-15")

        self.assertEqual(Level.objects.filter(name="Level 6").count(), 1)
        self.assertEqual(Exam.objects.filter(name="Level 6 Final Exam").count(), 1)
        self.assertEqual(ExamSection.objects.count(), 6)
