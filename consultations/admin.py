from myproject.admin_utils import AdminEditButtonMixin
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.http import Http404
from .models import Consultation
from accounts.models import is_demo_user, is_master_admin


class RealVsDemoConsultationFilter(admin.SimpleListFilter):
    title = "Data Source"
    parameter_name = "data_source"

    def lookups(self, request, model_admin):
        return (
            ("real", "👤 Real Customer Bookings"),
            ("demo", "🧪 Demo Bookings"),
        )

    def queryset(self, request, queryset):
        if self.value() == "real":
            return queryset.filter(is_demo=False)
        if self.value() == "demo":
            return queryset.filter(is_demo=True)
        return queryset


class AuthenticatedConsultationFilter(admin.SimpleListFilter):
    title = "User Type"
    parameter_name = "user_type"

    def lookups(self, request, model_admin):
        return (
            ("authenticated", "Authenticated Users"),
            ("guest", "Guest Users"),
        )

    def queryset(self, request, queryset):
        if self.value() == "authenticated":
            return queryset.filter(user__isnull=False)
        if self.value() == "guest":
            return queryset.filter(user__isnull=True)
        return queryset


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


@admin.register(Consultation)
class ConsultationAdmin(AdminEditButtonMixin, admin.ModelAdmin):
    list_display = (
        "edit_button",
        "id",
        "full_name",
        "email",
        "mobile",
        "date",
        "time_slot",
        "status",
        "get_data_source_badge",
        "user_type_display",
        "created_at",
    )
    list_display_links = ("id", "full_name")
    list_select_related = ("user",)
    show_full_result_count = False
    list_filter = (
        RealVsDemoConsultationFilter,
        EmailDropdownFilter,
        AuthenticatedConsultationFilter,
        "status",
        "date",
        "created_at",
    )
    search_fields = ("full_name", "email", "mobile", "topic")
    list_editable = ("status",)
    readonly_fields = ("created_at", "updated_at", "user", "is_demo")
    ordering = ("-created_at",)

    fieldsets = (
        ("Customer Details", {
            "fields": ("user", "full_name", "email", "mobile", "is_demo")
        }),
        ("Appointment", {
            "fields": ("date", "time_slot", "topic", "notes")
        }),
        ("Status & Timestamps", {
            "fields": ("status", "created_at", "updated_at")
        }),
    )

    def get_data_source_badge(self, obj):
        if obj.is_demo:
            return mark_safe('<span style="background-color: #d97706; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Demo Data</span>')
        return mark_safe('<span style="background-color: #16a34a; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Real Customer</span>')
    get_data_source_badge.short_description = "Source"

    def user_type_display(self, obj):
        return "Authenticated" if obj.user else "Guest"
    user_type_display.short_description = "User Type"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_demo_user(request.user):
            # Demo staff only sees demo bookings; real customer bookings are strictly isolated
            return qs.filter(is_demo=True)
        return qs

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if is_demo_user(request.user):
            try:
                consultation = Consultation.objects.get(pk=object_id)
                if not consultation.is_demo:
                    raise Http404("Consultation not found.")
            except (Consultation.DoesNotExist, ValueError):
                raise Http404("Consultation not found.")
        return super().change_view(request, object_id, form_url, extra_context)