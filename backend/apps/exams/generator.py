import random
from decimal import Decimal

from django.core.exceptions import ValidationError

from .models import Exam, ExamQuestion, ExamSourceAllocation


def validate_exam_configuration(configuration):
    allocations = configuration["allocations"]
    if sum(item["question_count"] for item in allocations) != configuration["question_count"]:
        raise ValidationError("Allocated question counts must equal the exam question count.")
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
    for item in configuration["allocations"]:
        available = list(item["source"].questions.filter(is_active=True).prefetch_related("choices"))
        selected.extend(random.sample(available, item["question_count"]))
    random.shuffle(selected)
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
