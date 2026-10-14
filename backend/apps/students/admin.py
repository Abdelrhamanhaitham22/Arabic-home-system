from django.contrib import admin

from apps.results.models import Result
from apps.teachers.models import TeacherAssessment, TeacherAssessmentConfig

from .models import Student, StudentPromotion


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_code",
        "full_name",
        "level",
        "phone_number",
        "preferred_language",
        "created_at",
    )
    search_fields = ("student_code", "full_name", "phone_number")
    list_filter = ("level", "preferred_language", "created_at")
    autocomplete_fields = ("level",)
    readonly_fields = ("student_code", "created_at", "updated_at")


@admin.register(StudentPromotion)
class StudentPromotionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "from_level",
        "to_level",
        "percentage",
        "source_attempt",
        "promoted_at",
    )
    list_filter = ("from_level", "to_level", "promoted_at")
    search_fields = ("student__student_code", "student__full_name")
    list_select_related = ("student", "from_level", "to_level", "source_attempt", "source_result")
    readonly_fields = tuple(field.name for field in StudentPromotion._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TeacherAssessment)
class TeacherAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "level",
        "written_score",
        "activity_dictation_score",
        "oral_score",
        "total_score",
        "is_complete",
        "completed_at",
    )
    list_filter = ("level", "is_complete", "completed_at")
    search_fields = ("student__student_code", "student__full_name")
    list_select_related = ("student", "level", "teacher")
    autocomplete_fields = ("student", "level", "teacher")
    readonly_fields = ("is_complete", "completed_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.is_complete:
            return
        config, _ = TeacherAssessmentConfig.objects.get_or_create(level=obj.level)
        total_score = obj.total_score
        total_max = config.total_max
        Result.objects.filter(student=obj.student, exam__level_id=obj.level_id).update(
            score=total_score,
            max_score=total_max,
            percentage=round((total_score / total_max) * 100, 2) if total_max else 0,
            published=True,
        )
