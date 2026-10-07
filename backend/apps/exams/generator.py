import random
from decimal import Decimal

from django.core.exceptions import ValidationError

from .models import Exam, ExamQuestion, ExamSourceAllocation


def validate_exam_configuration(configuration):
    allocations = configuration["allocations"]
    if sum(item["question_count"] for item in allocations) != configuration["question_count"]:
        raise ValidationError("Allocated question counts must equal the exam question count.")
    has_type_mix = "multiple_choice_count" in configuration or "true_false_count" in configuration
    required_multiple_choice = configuration.get("multiple_choice_count", 0)
    required_true_false = configuration.get("true_false_count", 0)
    if has_type_mix and required_multiple_choice + required_true_false != configuration["question_count"]:
        raise ValidationError("Multiple-choice and true/false counts must equal the exam question count.")
    if configuration["max_score"] <= Decimal("0"):
        raise ValidationError("The exam score must be greater than zero.")
    if configuration.get("opens_at") and configuration.get("closes_at") <= configuration["opens_at"]:
        raise ValidationError("Closing time must be after opening time.")
    seen_sources = set()
    for item in allocations:
        source = item["source"]
        if source.id in seen_sources:
            raise ValidationError("A question source can only be allocated once.")
        if source.level_id != configuration["level"].id:
            raise ValidationError("Every question source must belong to the selected level.")
        if item["question_count"] > source.question_count:
            raise ValidationError(f"{source.original_filename} does not contain enough active questions.")
        seen_sources.add(source.id)
    if has_type_mix:
        available_multiple_choice = sum(item["source"].questions.filter(is_active=True, question_type="multiple_choice").count() for item in allocations)
        available_true_false = sum(item["source"].questions.filter(is_active=True, question_type="true_false").count() for item in allocations)
        if required_multiple_choice > available_multiple_choice:
            raise ValidationError("The selected Word files do not contain enough multiple-choice questions.")
        if required_true_false > available_true_false:
            raise ValidationError("The selected Word files do not contain enough true/false questions.")


def create_exam(configuration):
    validate_exam_configuration(configuration)
    exam = Exam.objects.create(
        level=configuration["level"],
        name=configuration["name"],
        max_score=configuration["max_score"],
        question_count=configuration["question_count"],
        exam_date=configuration["exam_date"],
        time_limit_minutes=configuration.get("time_limit_minutes"),
        opens_at=configuration.get("opens_at"),
        closes_at=configuration.get("closes_at"),
    )
    ExamSourceAllocation.objects.bulk_create([
        ExamSourceAllocation(exam=exam, source=item["source"], question_count=item["question_count"])
        for item in configuration["allocations"]
    ])
    selected = []
    multiple_choice_count = configuration.get("multiple_choice_count", 0)
    source_selections = []
    if "multiple_choice_count" not in configuration and "true_false_count" not in configuration:
        for item in configuration["allocations"]:
            available = list(item["source"].questions.filter(is_active=True).prefetch_related("choices"))
            selected.extend(random.sample(available, item["question_count"]))
        random.shuffle(selected)
        return _save_selected_questions(exam, selected)
    for item in configuration["allocations"]:
        available = list(item["source"].questions.filter(is_active=True).prefetch_related("choices"))
        multiple_choice = [question for question in available if question.question_type == "multiple_choice"]
        true_false = [question for question in available if question.question_type == "true_false"]
        minimum_multiple_choice = max(0, item["question_count"] - len(true_false))
        maximum_multiple_choice = min(item["question_count"], len(multiple_choice))
        source_selections.append((multiple_choice, true_false, minimum_multiple_choice, maximum_multiple_choice, item["question_count"]))
    minimum_total = sum(selection[2] for selection in source_selections)
    if not minimum_total <= multiple_choice_count <= sum(selection[3] for selection in source_selections):
        raise ValidationError("The selected Word files cannot satisfy the requested question-type mix.")
    for index, (multiple_choice, true_false, minimum, maximum, requested_count) in enumerate(source_selections):
        future_minimum = sum(selection[2] for selection in source_selections[index + 1:])
        selected_multiple_choice = min(maximum, max(minimum, multiple_choice_count - future_minimum))
        multiple_choice_count -= selected_multiple_choice
        selected.extend(random.sample(multiple_choice, selected_multiple_choice))
        selected.extend(random.sample(true_false, requested_count - selected_multiple_choice))
    random.shuffle(selected)
    return _save_selected_questions(exam, selected)


def _save_selected_questions(exam, selected):
    ExamQuestion.objects.bulk_create([
        ExamQuestion(exam=exam, question=question, display_order=index)
        for index, question in enumerate(selected, start=1)
    ])
    return exam


def update_exam(exam, configuration):
    validate_exam_configuration(configuration)
    exam.name = configuration["name"]
    exam.max_score = configuration["max_score"]
    exam.question_count = configuration["question_count"]
    exam.exam_date = configuration["exam_date"]
    exam.time_limit_minutes = configuration.get("time_limit_minutes")
    exam.opens_at = configuration.get("opens_at")
    exam.closes_at = configuration.get("closes_at")
    exam.save()
    exam.source_allocations.all().delete()
    exam.selected_questions.all().delete()
    ExamSourceAllocation.objects.bulk_create([
        ExamSourceAllocation(exam=exam, source=item["source"], question_count=item["question_count"])
        for item in configuration["allocations"]
    ])
    selected = []
    for item in configuration["allocations"]:
        available = list(item["source"].questions.filter(is_active=True).prefetch_related("choices"))
        selected.extend(random.sample(available, item["question_count"]))
    random.shuffle(selected)
    ExamQuestion.objects.bulk_create([
        ExamQuestion(exam=exam, question=question, display_order=index)
        for index, question in enumerate(selected, start=1)
    ])
    return exam


def preview_exam_questions(exam):
    questions = [selected.question for selected in exam.selected_questions.select_related(
        "question__subject", "question__source"
    ).prefetch_related("question__choices")]
    points = exam.max_score / exam.question_count
    return [{
        "prompt": question.prompt,
        "subject": question.subject.name if question.subject_id else None,
        "source": question.source.original_filename if question.source_id else None,
        "question_type": question.question_type,
        "points": points,
        "choices": [choice.text for choice in question.choices.all()],
    } for question in questions]
