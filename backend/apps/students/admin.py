from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.utils import timezone

from apps.exams.models import Exam, Level
from apps.results.models import Result
from apps.teachers.models import TeacherAssessment, TeacherAssessmentConfig

from .models import Student, StudentPromotion, StudentPromotionRoster


class StudentLevelAssignmentForm(ActionForm):
    target_level = forms.ModelChoiceField(
        queryset=Level.objects.none(),
        label="Assign selected students to level",
        required=False,
    )
    target_exam = forms.ModelChoiceField(
        queryset=Exam.objects.none(),
        label="Assign selected students to exam",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target_level"].queryset = Level.objects.filter(is_active=True).order_by("order")
        self.fields["target_exam"].queryset = Exam.objects.filter(status="open").order_by("name")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_code",
        "full_name",
        "level",
        "assigned_exam",
        "phone_number",
        "preferred_language",
        "created_at",
    )
    search_fields = ("student_code", "full_name", "phone_number")
    list_filter = ("level", "assigned_exam", "preferred_language", "created_at")
    autocomplete_fields = ("level", "assigned_exam")
    readonly_fields = ("student_code", "created_at", "updated_at")
    action_form = StudentLevelAssignmentForm
    actions = ("assign_selected_students_to_level", "assign_selected_students_to_exam")

    @admin.action(description="Assign selected students to the chosen level")
    def assign_selected_students_to_level(self, request, queryset):
        target_level_id = request.POST.get("target_level")
        target_level = Level.objects.filter(pk=target_level_id, is_active=True).first()
        if target_level is None:
            self.message_user(
                request,
                "Choose an active level before assigning students.",
                level=messages.ERROR,
            )
            return

        student_ids = list(queryset.values_list("pk", flat=True))
        updated_count = Student.objects.filter(pk__in=student_ids).update(
            level=target_level,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f"Assigned {updated_count} student(s) to {target_level.name}.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Assign selected students to the chosen exam")
    def assign_selected_students_to_exam(self, request, queryset):
        exam = Exam.objects.filter(pk=request.POST.get("target_exam"), status="open").first()
        if exam is None:
            self.message_user(request, "Choose an open exam before assigning students.", level=messages.ERROR)
            return
        if queryset.exclude(level_id=exam.level_id).exists():
            self.message_user(request, "All selected students must be in the exam level.", level=messages.ERROR)
            return
        updated_count = queryset.update(assigned_exam=exam, updated_at=timezone.now())
        self.message_user(request, f"Assigned {updated_count} student(s) to {exam.name}.", level=messages.SUCCESS)


admin.site.register(StudentPromotionRoster, StudentAdmin)


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
        return True

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
