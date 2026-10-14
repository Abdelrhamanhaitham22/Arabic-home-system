from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from apps.attempts.models import ExamAttempt
from apps.exams.models import Level
from apps.results.models import Result
from apps.students.models import Student, StudentPromotion
from apps.teachers.models import TeacherAssessment, TeacherAssessmentConfig


PASS_PERCENTAGE = Decimal("50")


@dataclass(frozen=True)
class PromotionOutcome:
    status: str
    reason: str
    promotion: StudentPromotion | None = None


@dataclass(frozen=True)
class PromotionCandidate:
    attempt: ExamAttempt
    student: Student
    assessment: TeacherAssessment
    next_level: Level
    total_score: Decimal
    total_max: Decimal
    percentage: Decimal


def promote_student_from_attempt(attempt_id: int) -> PromotionOutcome:
    try:
        return _promote_attempt_transaction(attempt_id)
    except ExamAttempt.DoesNotExist:
        return PromotionOutcome("not_eligible", "attempt_not_found")


def assessment_promotion_status(assessment: TeacherAssessment) -> str:
    if not assessment.is_complete or assessment.completed_at is None:
        return "incomplete"
    promotion = StudentPromotion.objects.filter(
        student=assessment.student,
        from_level=assessment.level,
    ).order_by("-promoted_at").first()
    if promotion:
        if _promotion_scores_changed(assessment, promotion):
            return "review_required"
        return "promoted" if assessment.student.level_id == promotion.to_level_id else "review_required"
    if assessment.student.level_id != assessment.level_id:
        return "review_required"
    return _completed_assessment_status(assessment)


def _promotion_scores_changed(assessment, promotion):
    return (
        assessment.written_score != promotion.written_score
        or assessment.activity_dictation_score != promotion.activity_dictation_score
        or assessment.oral_score != promotion.oral_score
    )


def _completed_assessment_status(assessment):
    has_next_level = Level.objects.filter(
        is_active=True,
        order__gt=assessment.level.order,
    ).exists()
    if not has_next_level:
        return "highest_level"
    attempt = ExamAttempt.objects.filter(
        student=assessment.student,
        exam__level_id=assessment.level_id,
        status="submitted",
    ).order_by("-submitted_at", "-id").first()
    if attempt is None:
        return "awaiting_exam"
    candidate = _promotion_candidate(attempt, assessment.student)
    if isinstance(candidate, PromotionOutcome):
        return "below_threshold" if candidate.reason == "below_threshold" else "review_required"
    return "promotion_pending"


def _promote_attempt_transaction(attempt_id):
    with transaction.atomic():
        attempt = ExamAttempt.objects.select_related("exam").get(pk=attempt_id)
        student = Student.objects.select_for_update().get(pk=attempt.student_id)
        previous_promotion = StudentPromotion.objects.filter(source_attempt=attempt).first()
        if previous_promotion:
            return PromotionOutcome("already_promoted", "attempt_already_recorded", previous_promotion)
        return _evaluate_and_record(attempt, student)


def _evaluate_and_record(attempt, student):
    candidate = _promotion_candidate(attempt, student)
    if isinstance(candidate, PromotionOutcome):
        return candidate
    return _record_promotion(candidate)


def _record_promotion(candidate):
    promotion, created = StudentPromotion.objects.get_or_create(
        source_attempt=candidate.attempt,
        defaults=_promotion_record_fields(candidate),
    )
    if not created:
        return PromotionOutcome("already_promoted", "attempt_already_recorded", promotion)
    candidate.student.level = candidate.next_level
    candidate.student.save(update_fields=("level", "updated_at"))
    return PromotionOutcome("promoted", "passed_threshold", promotion)


def _promotion_record_fields(candidate):
    assessment = candidate.assessment
    return {
        "student": candidate.student,
        "source_result": Result.objects.filter(attempt=candidate.attempt).first(),
        "from_level": assessment.level,
        "to_level": candidate.next_level,
        "written_score": candidate.attempt.score,
        "activity_dictation_score": assessment.activity_dictation_score,
        "oral_score": assessment.oral_score,
        "total_score": candidate.total_score,
        "total_max": candidate.total_max,
        "percentage": candidate.percentage.quantize(Decimal("0.01")),
    }


def _promotion_candidate(attempt, student):
    assessment = _completed_assessment_for(attempt, student)
    if isinstance(assessment, PromotionOutcome):
        return assessment
    config = _valid_assessment_config(attempt, assessment)
    if isinstance(config, PromotionOutcome):
        return config
    next_level = Level.objects.filter(
        is_active=True,
        order__gt=assessment.level.order,
    ).order_by("order").first()
    if next_level is None:
        return PromotionOutcome("not_eligible", "no_next_active_level")
    total_score = attempt.score + assessment.activity_dictation_score + assessment.oral_score
    total_max = config.total_max
    percentage = total_score * Decimal("100") / total_max
    if percentage < PASS_PERCENTAGE:
        return PromotionOutcome("not_eligible", "below_threshold")
    return PromotionCandidate(attempt, student, assessment, next_level, total_score, total_max, percentage)


def _completed_assessment_for(attempt, student):
    if attempt.status != "submitted" or attempt.submitted_at is None:
        return PromotionOutcome("not_eligible", "exam_not_submitted")
    assessed_level_id = attempt.exam.level_id
    if assessed_level_id is None or student.level_id != assessed_level_id:
        return PromotionOutcome("not_eligible", "student_level_mismatch")
    assessment = TeacherAssessment.objects.filter(
        student=student,
        level_id=assessed_level_id,
    ).first()
    if assessment is None or not assessment.is_complete or assessment.completed_at is None:
        return PromotionOutcome("not_eligible", "teacher_assessment_incomplete")
    return assessment


def _valid_assessment_config(attempt, assessment):
    assessed_level_id = assessment.level_id
    config = TeacherAssessmentConfig.objects.filter(level_id=assessed_level_id).first()
    if config is None:
        return PromotionOutcome("not_eligible", "assessment_config_missing")
    if attempt.max_score <= 0 or config.written_max != attempt.max_score:
        return PromotionOutcome("not_eligible", "written_max_mismatch")
    if config.total_max <= 0:
        return PromotionOutcome("not_eligible", "combined_max_invalid")
    if attempt.score < 0 or attempt.score > attempt.max_score:
        return PromotionOutcome("not_eligible", "exam_score_invalid")
    if (
        assessment.activity_dictation_score < 0
        or assessment.activity_dictation_score > config.activity_dictation_max
        or assessment.oral_score < 0
        or assessment.oral_score > config.oral_max
    ):
        return PromotionOutcome("not_eligible", "teacher_score_invalid")
    return config
