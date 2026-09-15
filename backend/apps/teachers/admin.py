from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import TeacherProfile


User = get_user_model()


class NonTeacherUserAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(teacher_profile__isnull=True)


admin.site.unregister(User)
admin.site.register(User, NonTeacherUserAdmin)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_approved", "assigned_levels")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    list_filter = ("is_approved",)
    filter_horizontal = ("levels",)

    @admin.display(description="Assigned levels")
    def assigned_levels(self, profile):
        return ", ".join(profile.levels.values_list("name", flat=True)) or "None"
