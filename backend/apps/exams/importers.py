import csv
import io

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Level, Question, QuestionChoice


CSV_COLUMNS = (
    "bank_order", "prompt", "question_type", "points",
    "choice_1", "choice_1_correct", "choice_2", "choice_2_correct",
    "choice_3", "choice_3_correct", "choice_4", "choice_4_correct",
)


def parse_boolean(raw_value, row_number, column_name):
    normalized = raw_value.strip().lower()
    if normalized not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValidationError(f"Row {row_number}: {column_name} must be true or false.")
    return normalized in {"true", "1", "yes"}


def parse_question_row(row, row_number):
    try:
        bank_order = int(row["bank_order"])
        points = int(row["points"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValidationError(f"Row {row_number}: bank_order and points must be whole numbers.") from error
    if bank_order < 1 or points < 1 or not row["prompt"].strip():
        raise ValidationError(f"Row {row_number}: bank_order, points, and prompt are required.")
    question_type = row["question_type"].strip().lower()
    if question_type not in {"true_false", "multiple_choice"}:
        raise ValidationError(f"Row {row_number}: question_type must be true_false or multiple_choice.")

    choices = []
    for choice_number in range(1, 5):
        text = row.get(f"choice_{choice_number}", "").strip()
        if not text:
            continue
        choices.append((text, parse_boolean(row.get(f"choice_{choice_number}_correct", ""), row_number, f"choice_{choice_number}_correct")))
    if len(choices) < 2 or sum(is_correct for _, is_correct in choices) != 1:
        raise ValidationError(f"Row {row_number}: add at least two choices and exactly one correct choice.")
    if question_type == "true_false" and len(choices) != 2:
        raise ValidationError(f"Row {row_number}: true_false questions must have exactly two choices.")
    return bank_order, row["prompt"].strip(), question_type, points, choices


def import_question_bank(level, uploaded_file):
    try:
        text = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValidationError("The CSV file must use UTF-8 encoding.") from error
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != list(CSV_COLUMNS):
        raise ValidationError("CSV columns must be: " + ", ".join(CSV_COLUMNS))

    parsed_rows = []
    seen_orders = set()
    for row_number, row in enumerate(reader, start=2):
        parsed_row = parse_question_row(row, row_number)
        if parsed_row[0] in seen_orders:
            raise ValidationError(f"Row {row_number}: bank_order is duplicated in the file.")
        seen_orders.add(parsed_row[0])
        parsed_rows.append(parsed_row)
    if not parsed_rows:
        raise ValidationError("The CSV file does not contain any questions.")
    existing_orders = set(level.question_bank.filter(bank_order__in=seen_orders).values_list("bank_order", flat=True))
    if existing_orders:
        raise ValidationError("These bank orders already exist: " + ", ".join(map(str, sorted(existing_orders))))

    with transaction.atomic():
        for bank_order, prompt, question_type, points, choices in parsed_rows:
            question = Question.objects.create(
                level=level, prompt=prompt, question_type=question_type,
                points=points, order=bank_order, bank_order=bank_order,
            )
            QuestionChoice.objects.bulk_create([
                QuestionChoice(question=question, text=text, order=index, is_correct=is_correct)
                for index, (text, is_correct) in enumerate(choices, start=1)
            ])
    return len(parsed_rows)
