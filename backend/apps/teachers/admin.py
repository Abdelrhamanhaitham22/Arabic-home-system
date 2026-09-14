from django.contrib import admin

from .models import TeacherProfile


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_approved", "assigned_levels")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    list_filter = ("is_approved",)
    filter_horizontal = ("levels",)

    @admin.display(description="Assigned levels")
    def assigned_levels(self, profile):
        return ", ".join(profile.levels.values_list("name", flat=True)) or "None"
