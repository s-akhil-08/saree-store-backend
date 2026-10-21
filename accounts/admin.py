from myproject.admin_utils import AdminEditButtonMixin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.conf import settings
from django.http import Http404
from django.utils.safestring import mark_safe
from .models import Profile, OTP, TempUser, DEMO_USERNAMES, is_demo_user, is_master_admin


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"


class UserTypeFilter(admin.SimpleListFilter):
    title = "Account Type"
    parameter_name = "account_type"

    def lookups(self, request, model_admin):
        return (
            ("real", "👤 Real Users"),
            ("demo", "🧪 Demo Accounts"),
            ("staff", "🛡️ Staff / Admins"),
        )

    def queryset(self, request, queryset):
        if self.value() == "real":
            return queryset.filter(is_staff=False, is_superuser=False).exclude(
                profile__is_demo=True
            ).exclude(username__in=DEMO_USERNAMES)
        if self.value() == "demo":
            return queryset.filter(
                models.Q(profile__is_demo=True) | models.Q(username__in=DEMO_USERNAMES)
            )
        if self.value() == "staff":
            return queryset.filter(models.Q(is_staff=True) | models.Q(is_superuser=True))
        return queryset


from django.db import models


class UserAdmin(AdminEditButtonMixin, BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "get_first_name",
        "get_last_name",
        "get_mobile",
        "get_account_type",
        "is_staff",
        "is_active",
        "date_joined",
        "edit_button",
    )
    list_display_links = ("username", "email")
    list_filter = (UserTypeFilter, "is_staff", "is_active", "date_joined")
    list_select_related = ("profile",)
    show_full_result_count = False

    def get_first_name(self, instance):
        return instance.profile.first_name if hasattr(instance, "profile") else (instance.first_name or "-")
    get_first_name.short_description = "First name"

    def get_last_name(self, instance):
        return instance.profile.last_name if hasattr(instance, "profile") else (instance.last_name or "-")
    get_last_name.short_description = "Last name"

    def get_mobile(self, instance):
        return instance.profile.mobile if hasattr(instance, "profile") else "-"
    get_mobile.short_description = "Mobile"

    def get_account_type(self, instance):
        if is_master_admin(instance):
            return mark_safe('<span style="background-color: #6b21a8; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Master Admin</span>')
        elif is_demo_user(instance):
            return mark_safe('<span style="background-color: #d97706; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Demo Account</span>')
        else:
            return mark_safe('<span style="background-color: #16a34a; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Real User</span>')
    get_account_type.short_description = "Account Type"

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_demo_user(request.user):
            # Demo accounts only see demo users; real users and master admins are completely isolated
            return qs.filter(
                models.Q(profile__is_demo=True) | models.Q(username__in=DEMO_USERNAMES)
            )
        return qs

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if is_demo_user(request.user):
            try:
                target_user = User.objects.get(pk=object_id)
                if not is_demo_user(target_user):
                    raise Http404("User not found.")
            except (User.DoesNotExist, ValueError):
                raise Http404("User not found.")
        return super().change_view(request, object_id, form_url, extra_context)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "first_name", "last_name", "mobile", "get_account_type", "is_demo")
    list_filter = ("is_demo",)
    search_fields = ("user__email", "user__username", "mobile", "first_name", "last_name")

    def get_account_type(self, instance):
        if is_demo_user(instance.user) or instance.is_demo:
            return mark_safe('<span style="background-color: #d97706; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Demo</span>')
        return mark_safe('<span style="background-color: #16a34a; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Real User</span>')
    get_account_type.short_description = "Type"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_demo_user(request.user):
            return qs.filter(
                models.Q(is_demo=True) | models.Q(user__username__in=DEMO_USERNAMES)
            )
        return qs

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if is_demo_user(request.user):
            try:
                profile = Profile.objects.get(pk=object_id)
                if not (profile.is_demo or is_demo_user(profile.user)):
                    raise Http404("Profile not found.")
            except (Profile.DoesNotExist, ValueError):
                raise Http404("Profile not found.")
        return super().change_view(request, object_id, form_url, extra_context)


class EmailDropdownFilter(admin.SimpleListFilter):
    title = 'email'
    parameter_name = 'email'
    template = 'admin/dropdown_filter.html'

    def lookups(self, request, model_admin):
        emails = model_admin.model.objects.exclude(email__isnull=True).exclude(email__exact="").values_list('email', flat=True).distinct().order_by('email')[:100]
        return [(email, email) for email in emails if email]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(email=self.value())
        return queryset


@admin.register(OTP)
class OTPAdmin(AdminEditButtonMixin, admin.ModelAdmin):
    list_display = ("email", "code", "purpose", "created_at", "is_used", "edit_button")
    list_display_links = ("email",)
    list_filter = (EmailDropdownFilter, "purpose", "is_used")
    search_fields = ("email",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_demo_user(request.user):
            # Demo accounts cannot see real OTP records
            return qs.none()
        return qs


@admin.register(TempUser)
class TempUserAdmin(AdminEditButtonMixin, admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "mobile", "created_at", "edit_button")
    list_display_links = ("email",)
    search_fields = ("email", "first_name", "last_name", "mobile")
    readonly_fields = ("password", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_demo_user(request.user):
            # Demo accounts cannot see real pending user registrations
            return qs.none()
        return qs


# =====================================================================
# LOG ENTRY / ADMIN ACTIVITY LOGS WITH STRICT DEMO ISOLATION & FILTERS
# =====================================================================
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION


class RealVsDemoLogFilter(admin.SimpleListFilter):
    title = "Admin Source"
    parameter_name = "admin_source"

    def lookups(self, request, model_admin):
        return (
            ("master", "👑 Master Admin Actions"),
            ("demo", "🧪 Demo Staff Actions"),
        )

    def queryset(self, request, queryset):
        if self.value() == "master":
            return queryset.exclude(user__profile__is_demo=True).exclude(user__username__in=DEMO_USERNAMES)
        if self.value() == "demo":
            return queryset.filter(models.Q(user__profile__is_demo=True) | models.Q(user__username__in=DEMO_USERNAMES))
        return queryset


class ActionTypeFilter(admin.SimpleListFilter):
    title = "Action Type"
    parameter_name = "action_type"

    def lookups(self, request, model_admin):
        return (
            (str(ADDITION), "➕ Added"),
            (str(CHANGE), "✏️ Changed"),
            (str(DELETION), "🗑️ Deleted"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(action_flag=int(self.value()))
        return queryset


class CustomLogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "action_time",
        "user_display",
        "action_flag_badge",
        "content_type",
        "object_repr",
        "change_message",
    )
    list_filter = (
        RealVsDemoLogFilter,
        ActionTypeFilter,
        "content_type",
        "action_time",
    )
    search_fields = (
        "user__username",
        "user__email",
        "object_repr",
        "change_message",
    )
    date_hierarchy = "action_time"
    list_per_page = 20
    ordering = ("-action_time",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def user_display(self, obj):
        if not obj.user:
            return "-"
        if is_demo_user(obj.user):
            return mark_safe(f'<strong>{obj.user.username}</strong> <span style="background-color: #d97706; color: #fff; padding: 1px 6px; border-radius: 9999px; font-size: 10px; font-weight: bold;">Demo</span>')
        return mark_safe(f'<strong>{obj.user.username}</strong> <span style="background-color: #6b21a8; color: #fff; padding: 1px 6px; border-radius: 9999px; font-size: 10px; font-weight: bold;">Master</span>')
    user_display.short_description = "Admin User"

    def action_flag_badge(self, obj):
        flag = obj.action_flag
        if flag == ADDITION:
            return mark_safe('<span style="background-color: #16a34a; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Added</span>')
        elif flag == CHANGE:
            return mark_safe('<span style="background-color: #2563eb; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Changed</span>')
        elif flag == DELETION:
            return mark_safe('<span style="background-color: #dc2626; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Deleted</span>')
        return obj.get_action_flag_display()
    action_flag_badge.short_description = "Action"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_demo_user(request.user):
            # Demo staff ONLY sees demo activity; main admin activity is strictly hidden
            return qs.filter(
                models.Q(user__profile__is_demo=True) | models.Q(user__username__in=DEMO_USERNAMES)
            )
        return qs


if LogEntry in admin.site._registry:
    admin.site.unregister(LogEntry)
admin.site.register(LogEntry, CustomLogEntryAdmin)
