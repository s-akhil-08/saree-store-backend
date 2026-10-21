from django.utils.html import format_html
from django.urls import reverse
import myproject.admin_pagination  # Initialize dynamic pagination hooks globally


class AdminEditButtonMixin:
    """
    Mixin for Django ModelAdmin classes.
    Adds a prominent, clearly visible 'Edit' button column in the admin changelist
    seamlessly matching the existing Django Daisy design system and active theme.
    """

    def edit_button(self, obj):
        if not obj or not getattr(obj, "pk", None):
            return ""
        opts = obj._meta
        url = reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk])
        return format_html(
            '<a href="{}" class="btn btn-xs btn-primary gap-1 font-semibold shadow-xs hover:scale-105 transition-all" '
            'style="display: inline-flex; align-items: center; justify-content: center; text-decoration: none; '
            'padding: 3px 10px; border-radius: 6px; font-size: 11px; white-space: nowrap;">'
            '<i class="fa-solid fa-pen-to-square text-[10px]"></i> Edit'
            '</a>',
            url,
        )

    edit_button.short_description = "Action"
    edit_button.allow_tags = True
