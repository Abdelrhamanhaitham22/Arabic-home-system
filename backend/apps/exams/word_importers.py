from django.core.exceptions import ValidationError
from django.db import transaction
from docx import Document

from .models import Level, Question, QuestionChoice, QuestionSource, Subject


FIELD_NAMES = {
    "question": "question",
    "option 1": "option_1",
    "option 2": "option_2",
    "option 3": "option_3",
    "option 4": "option_4",
    "correct answer": "correct_answer",
    "question type": "question_type",
}


def read_question_blocks(uploaded_file):
    document = Document(uploaded_file)
    blocks, block = [], {}
    started = False
    for paragraph in document.paragraphs:
        line = paragraph.text.strip()
        if not line:
            if block:
                blocks.append(block)
                block = {}
            continue
        if not started and not line.lower().startswith("question:"):
            continue
        started = True
        if ":" not in line:
            raise ValidationError(f"Invalid line: {line}")
        label, value = line.split(":", 1)
        field = FIELD_NAMES.get(label.strip().lower())
        if field is None or not value.strip() or field in block:
            raise ValidationError(f"Invalid or duplicate field: {label.strip()}")
        block[field] = value.strip()
    if block:
        blocks.append(block)
    if not blocks:
        raise ValidationError("The Word document contains no question blocks.")
    return blocks


def parse_question_block(block, bank_order):
    required = {"question", "option_1", "option_2", "correct_answer", "question_type"}
    missing = required - block.keys()
    if missing:
        raise ValidationError(f"Question {bank_order} is missing: {', '.join(sorted(missing))}.")
    question_type = block["question_type"].lower()
    option_fields = [f"option_{number}" for number in range(1, 5) if f"option_{number}" in block]
    if question_type not in {"multiple_choice", "true_false"}:
        raise ValidationError(f"Question {bank_order} has an invalid question type.")
    if question_type == "true_false" and {block[field].lower() for field in option_fields} != {"true", "false"}:
        raise ValidationError(f"Question {bank_order} true_false choices must be True and False.")
    choices = [(block[field], block[field] == block["correct_answer"]) for field in option_fields]
    if sum(correct for _, correct in choices) != 1:
        raise ValidationError(f"Question {bank_order} must have exactly one correct answer.")
    return block["question"], question_type, choices


def parse_uploaded_word_file(uploaded_file, start_order):
    try:
        blocks = read_question_blocks(uploaded_file)
        return [parse_question_block(block, start_order + index) for index, block in enumerate(blocks)]
    except ValidationError:
        raise
    except Exception as error:
        raise ValidationError("The uploaded file is not a readable Word document.") from error


def import_question_banks_from_word(level: Level, subject: Subject, uploaded_files):
    if subject.level_id != level.id:
        raise ValidationError("The selected subject must belong to this level.")
    if not uploaded_files:
        raise ValidationError("Choose at least one Word file.")

    next_order = level.question_bank.count() + 1
    parsed_files = []
    for uploaded_file in uploaded_files:
        parsed = parse_uploaded_word_file(uploaded_file, next_order)
        parsed_files.append((uploaded_file, parsed))
        next_order += len(parsed)

    with transaction.atomic():
        next_order = level.question_bank.count() + 1
        for uploaded_file, parsed in parsed_files:
            uploaded_file.seek(0)
            source = QuestionSource.objects.create(
                level=level,
                subject=subject,
                file=uploaded_file,
                original_filename=uploaded_file.name,
            )
            for bank_order, (prompt, question_type, choices) in enumerate(parsed, start=next_order):
                question = Question.objects.create(
                    level=level,
                    subject=subject,
                    source=source,
                    prompt=prompt,
                    question_type=question_type,
                    points=1,
                    order=bank_order,
                    bank_order=bank_order,
                )
                QuestionChoice.objects.bulk_create([
                    QuestionChoice(question=question, text=text, order=index, is_correct=is_correct)
                    for index, (text, is_correct) in enumerate(choices, start=1)
                ])
            next_order += len(parsed)
    return sum(len(parsed) for _, parsed in parsed_files)
