from django.contrib import admin
from adminsortable2.admin import SortableAdminMixin
from .models import Category, Product, NewArrivalProduct, WishlistItem, ContactLog, ProductVariantItem, ProductGalleryItem
from myproject.admin_utils import AdminEditButtonMixin

from django.db import models
from django.forms import Textarea


@admin.register(Category)
class CategoryAdmin(AdminEditButtonMixin, admin.ModelAdmin):
    list_display = ("order", "id", "name", "image", "image_file", "edit_button")
    list_display_links = ("id", "name")
    search_fields = ("id", "name")
    ordering = ("order", "id")
    prepopulated_fields = {"id": ("name",)}      # auto-generate slug from name

    fieldsets = (
        (None, {
            "fields": ("id", "name", "order", "image", "image_file")
        }),
    )

    class Media:
        css = {
            "all": ("admin/css/sortable_custom.css",)
        }
        js = (
            "admin/js/admin_file_preserver.js",
            "admin/js/categories_dragdrop.js",
        )


from django import forms
from django.forms import ModelForm
from django.utils.html import mark_safe


class VariantChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.color if getattr(obj, "color", None) else str(obj)

    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, str) and value.startswith("COLOR:"):
            return value
        try:
            return super().to_python(value)
        except Exception:
            try:
                return ProductVariantItem.objects.filter(pk=value).first()
            except Exception:
                return None

    def valid_value(self, value):
        return True


class ProductGalleryItemForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "variant" in self.fields:
            self.fields["variant"].empty_label = "-- Main Product Gallery --"
            self.fields["variant"].required = False

    def clean(self):
        cleaned_data = super().clean()
        raw_val = self.data.get(self.add_prefix("variant"))
        if isinstance(raw_val, str) and raw_val.startswith("COLOR:"):
            color_name = raw_val.replace("COLOR:", "").strip()
            self.instance._temp_color = color_name
        elif cleaned_data.get("variant") and getattr(cleaned_data["variant"], "color", None):
            self.instance._temp_color = cleaned_data["variant"].color
        return cleaned_data

    def clean_variant(self):
        try:
            variant = self.cleaned_data.get("variant")
            raw_val = self.data.get(self.add_prefix("variant")) or variant
            if isinstance(raw_val, str) and raw_val.startswith("COLOR:"):
                color_name = raw_val.replace("COLOR:", "").strip()
                self.instance._temp_color = color_name
                product_id = None
                if self.instance and getattr(self.instance, "product_id", None):
                    product_id = self.instance.product_id

                if product_id:
                    var_obj = ProductVariantItem.objects.filter(
                        product_id=product_id,
                        color__iexact=color_name
                    ).first()
                    if var_obj:
                        return var_obj
                return None

            if isinstance(variant, ProductVariantItem):
                self.instance._temp_color = variant.color
                return variant

            if variant and isinstance(variant, (int, str)) and str(variant).isdigit():
                var_obj = ProductVariantItem.objects.filter(pk=variant).first()
                if var_obj:
                    self.instance._temp_color = var_obj.color
                    return var_obj
        except Exception:
            return None

        return None



class ProductVariantItemInline(admin.TabularInline):
    model = ProductVariantItem
    extra = 0
    fields = ("color", "image_file", "image", "is_main")
    verbose_name = "Product Variant / Color"
    verbose_name_plural = "Product Colors / Variants (Main Image Upload)"


class ProductGalleryItemInline(admin.TabularInline):
    model = ProductGalleryItem
    form = ProductGalleryItemForm
    extra = 0
    fields = ("variant", "image_file", "image")
    verbose_name = "Gallery File Upload"
    verbose_name_plural = "Product & Variant Gallery Uploads"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "variant":
            kwargs["form_class"] = VariantChoiceField
            object_id = None
            if request and getattr(request, "resolver_match", None):
                match = request.resolver_match
                object_id = (
                    match.kwargs.get("object_id")
                    or match.kwargs.get("pk")
                )
                if not object_id and match.args:
                    object_id = match.args[0]

            if object_id:
                kwargs["queryset"] = ProductVariantItem.objects.filter(product_id=object_id)
            else:
                kwargs["queryset"] = ProductVariantItem.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(NewArrivalProduct)
class NewArrivalProductAdmin(AdminEditButtonMixin, admin.ModelAdmin):
    list_display = ("new_arrival_order", "id", "name", "category", "created_at", "edit_button")
    list_display_links = ("id", "name")
    list_select_related = ("category",)
    show_full_result_count = False
    ordering = ("new_arrival_order", "-created_at")

    class Media:
        css = {
            "all": ("admin/css/sortable_custom.css",)
        }
        js = ("admin/js/new_arrivals_dragdrop.js",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_new_arrival=True)





@admin.register(Product)
class ProductAdmin(AdminEditButtonMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "brand",
        "category",
        "is_new_arrival",
        "new_arrival_order",
        "created_at",
        "edit_button",
    )
    list_display_links = ("id", "name")
    list_select_related = ("category",)
    show_full_result_count = False
    list_filter = ("category", "is_new_arrival", "brand")
    search_fields = ("id", "name", "brand", "description")
    actions = ["batch_edit_products"]
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductVariantItemInline, ProductGalleryItemInline]

    @admin.action(description="⚡ Batch Edit Selected Products")
    def batch_edit_products(self, request, queryset):
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        from django.contrib import messages
        selected_ids = list(queryset.values_list("id", flat=True)[:10])
        if not selected_ids:
            self.message_user(request, "Please select at least 1 product to batch edit.", level=messages.WARNING)
            return None
        first_id = selected_ids[0]
        ids_str = ",".join(str(i) for i in selected_ids)
        url = reverse("admin:products_product_change", args=[first_id]) + f"?batch_ids={ids_str}"
        return HttpResponseRedirect(url)

    class Media:
        css = {
            "all": ("admin/css/admin_dropdown_fix.css",)
        }
        js = (
            "admin/js/variant_refresh.js",
            "admin/js/admin_file_preserver.js",
            "admin/js/batch_product_creator.js",
            "admin/js/batch_product_editor.js",
        )

    # Better editing experience for JSON fields
    formfield_overrides = {
        models.JSONField: {
            "widget": Textarea(attrs={"rows": 6, "cols": 80, "style": "font-family: monospace;"})
        },
    }

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "id",
                "name",
                "brand",
                "category",
                "is_new_arrival",
                "new_arrival_order",
                "image_file",
                "image",
            )
        }),
        ("Details", {
            "fields": (
                "description",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def save_formset(self, request, form, formset, change):
        import os
        from django.utils.text import slugify
        from .supabase_storage import supabase_storage

        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()

        # Handle ProductGalleryItem inline formset: match COLOR: dropdown values & relocate files to color folder
        if formset.model == ProductGalleryItem:
            for gallery_form in formset.forms:
                if not gallery_form.instance or not gallery_form.instance.pk:
                    continue
                gallery_item = gallery_form.instance
                raw_val = gallery_form.data.get(gallery_form.add_prefix("variant")) or ""
                color_name = None
                if isinstance(raw_val, str) and raw_val.startswith("COLOR:"):
                    color_name = raw_val.replace("COLOR:", "").strip()
                elif getattr(gallery_item, "variant", None) and getattr(gallery_item.variant, "color", None):
                    color_name = gallery_item.variant.color

                if color_name and gallery_item.product_id:
                    var_obj = ProductVariantItem.objects.filter(
                        product_id=gallery_item.product_id,
                        color__iexact=color_name
                    ).first()

                    if var_obj and gallery_item.variant_id != var_obj.id:
                        gallery_item.variant = var_obj
                        gallery_item.save(update_fields=["variant"])

                    # If image_file was uploaded before variant link was set (placed in main or unknown folder), relocate it to color folder
                    if gallery_item.image_file and gallery_item.image_file.name and var_obj:
                        color_slug = slugify(var_obj.color) if var_obj.color else "main"
                        old_name = gallery_item.image_file.name
                        filename = os.path.basename(old_name)
                        expected_name = f"products/{gallery_item.product_id}/{color_slug}/{filename}"

                        if old_name != expected_name:
                            success = supabase_storage.move(old_name, expected_name)
                            if success:
                                gallery_item.image_file.name = expected_name
                                gallery_item.save(update_fields=["image_file"])




from accounts.models import is_demo_user, DEMO_USERNAMES


class RealVsDemoWishlistFilter(admin.SimpleListFilter):
    title = "User Account Type"
    parameter_name = "account_type"

    def lookups(self, request, model_admin):
        return (
            ("real", "👤 Real Users"),
            ("demo", "🧪 Demo Accounts"),
        )

    def queryset(self, request, queryset):
        if self.value() == "real":
            return queryset.exclude(user__profile__is_demo=True).exclude(user__username__in=DEMO_USERNAMES)
        if self.value() == "demo":
            return queryset.filter(models.Q(user__profile__is_demo=True) | models.Q(user__username__in=DEMO_USERNAMES))
        return queryset


class RealVsDemoContactFilter(admin.SimpleListFilter):
    title = "Data Source"
    parameter_name = "data_source"

    def lookups(self, request, model_admin):
        return (
            ("real", "👤 Real Inquiries"),
            ("demo", "🧪 Demo Logs"),
        )

    def queryset(self, request, queryset):
        if self.value() == "real":
            return queryset.filter(is_demo=False)
        if self.value() == "demo":
            return queryset.filter(is_demo=True)
        return queryset


@admin.register(WishlistItem)
class WishlistItemAdmin(AdminEditButtonMixin, admin.ModelAdmin):
    list_display = ("user", "product", "get_account_type", "created_at", "edit_button")
    list_display_links = ("user", "product")
    list_select_related = ("user", "product")
    show_full_result_count = False
    list_filter = (RealVsDemoWishlistFilter, "created_at")
    search_fields = ("user__email", "product__name", "product__id")
    raw_id_fields = ("user", "product")

    def get_account_type(self, obj):
        if is_demo_user(obj.user):
            return mark_safe('<span style="background-color: #d97706; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Demo User</span>')
        return mark_safe('<span style="background-color: #16a34a; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Real User</span>')
    get_account_type.short_description = "User Type"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_demo_user(request.user):
            return qs.filter(models.Q(user__profile__is_demo=True) | models.Q(user__username__in=DEMO_USERNAMES))
        return qs


@admin.register(ContactLog)
class ContactLogAdmin(AdminEditButtonMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "who",
        "product",
        "guest_mobile",
        "get_data_source_badge",
        "created_at",
        "edit_button",
    )
    list_display_links = ("id", "who")
    list_select_related = ("user", "product")
    show_full_result_count = False
    list_filter = (
        RealVsDemoContactFilter,
        ("user", admin.EmptyFieldListFilter),   # separates Authenticated vs Guest
        "created_at",
    )
    search_fields = (
        "user__email",
        "guest_name",
        "guest_mobile",
        "product__name",
        "product__id",
    )
    readonly_fields = ("created_at", "is_demo")
    autocomplete_fields = ("product",)          # nice dropdown for product
    ordering = ("-created_at",)

    def get_data_source_badge(self, obj):
        if obj.is_demo:
            return mark_safe('<span style="background-color: #d97706; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Demo Data</span>')
        return mark_safe('<span style="background-color: #16a34a; color: #fff; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">Real Customer</span>')
    get_data_source_badge.short_description = "Source"

    def who(self, obj):
        if obj.user:
            return f"{obj.user.email} (Authenticated)"
        return f"{obj.guest_name or 'Guest'} (Guest)"
    who.short_description = "User / Guest"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_demo_user(request.user):
            return qs.filter(is_demo=True)
        return qs



from .models import GadwalWeavingShowcase, GadwalWeavingImage
from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminBase

class GadwalWeavingImageInline(SortableInlineAdminMixin, admin.TabularInline):
    model = GadwalWeavingImage
    extra = 1
    fields = ("order", "image_file", "image_url", "caption")
    ordering = ("order",)


@admin.register(GadwalWeavingShowcase)
class GadwalWeavingShowcaseAdmin(SortableAdminBase, AdminEditButtonMixin, admin.ModelAdmin):
    list_display = ("heading", "button_text", "button_link", "is_active", "updated_at", "edit_button")
    list_display_links = ("heading",)
    list_editable = ("is_active",)
    inlines = [GadwalWeavingImageInline]
    fieldsets = (
        (None, {
            "fields": ("heading", "description", "button_text", "button_link", "is_active")
        }),
    )

    class Media:
        js = ("admin/js/admin_file_preserver.js",)


