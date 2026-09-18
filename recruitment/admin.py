from django.contrib import admin

from .models import Application, Profile, PromotionCode, RecruitmentSettings, Team


@admin.register(RecruitmentSettings)
class RecruitmentSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_open', 'close_date')

    def has_add_permission(self, request):
        return not RecruitmentSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'division', 'sort_order', 'partner', 'is_recruiting')
    list_filter = ('division', 'is_recruiting')
    list_editable = ('sort_order', 'is_recruiting')
    filter_horizontal = ('leads',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'role', 'contact_method', 'onboarded_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'display_name')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'applicant', 'status', 'current_team', 'first_pick',
        'alternative', 'wildcard', 'submitted_at',
    )
    list_filter = ('status', 'first_pick')
    search_fields = ('applicant__username', 'applicant__email', 'major')


@admin.register(PromotionCode)
class PromotionCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'application', 'created_by', 'created_at', 'used_at')
