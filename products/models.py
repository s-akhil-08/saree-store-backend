from .supabase_storage import supabase_storage
from django.db import models
from django.utils.text import slugify
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
import os
import re


class HistoricalUsedID(models.Model):
    id_type = models.CharField(max_length=20, db_index=True)  # 'category' or 'product'
    used_id = models.CharField(max_length=100, unique=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historical Used ID"
        verbose_name_plural = "Historical Used IDs"

    def __str__(self):
        return f"{self.id_type}: {self.used_id}"


class CategoryIDSequence(models.Model):
    id = models.IntegerField(primary_key=True, default=1)
    last_number = models.PositiveIntegerField(default=0)


class ProductIDSequence(models.Model):
    category = models.OneToOneField("Category", primary_key=True, on_delete=models.CASCADE, related_name="id_sequence")
    last_number = models.PositiveIntegerField(default=0)


def is_id_used(used_id, exclude_category_pk=None, exclude_product_pk=None):
    """Check if an ID exists in active DB or in HistoricalUsedID table."""
    if not used_id:
        return False
    used_id_str = str(used_id).strip()
    if HistoricalUsedID.objects.filter(used_id=used_id_str).exists():
        return True

    cat_qs = Category.objects.filter(id=used_id_str)
    if exclude_category_pk:
        cat_qs = cat_qs.exclude(pk=exclude_category_pk)
    if cat_qs.exists():
        return True

    prod_qs = Product.objects.filter(id=used_id_str)
    if exclude_product_pk:
        prod_qs = prod_qs.exclude(pk=exclude_product_pk)
    if prod_qs.exists():
        return True

    return False


def record_used_id(id_type, used_id):
    """Record an ID into HistoricalUsedID table so it can never be reused."""
    if used_id:
        used_id_str = str(used_id).strip()
        HistoricalUsedID.objects.get_or_create(used_id=used_id_str, defaults={"id_type": id_type})


def category_image_path(instance, filename):
    return f"categories/{instance.id}/{filename}"


def product_main_image_path(instance, filename):
    return f"products/{instance.id}/main/{filename}"


def product_variant_image_path(instance, filename):
    p_id = getattr(instance, "product_id", None) or (instance.product.id if getattr(instance, "product", None) else "unknown")
    color_slug = slugify(instance.color) if instance.color else "main"
    return f"products/{p_id}/{color_slug}/{filename}"


def product_gallery_path(instance, filename):
    p_id = None
    color_slug = "main"

    if getattr(instance, "variant", None) and getattr(instance.variant, "color", None):
        color_slug = slugify(instance.variant.color)
        p_id = getattr(instance.variant, "product_id", None) or (instance.variant.product.id if getattr(instance.variant, "product", None) else None)
    elif getattr(instance, "_temp_color", None):
        color_slug = slugify(instance._temp_color)

    if not p_id:
        p_id = getattr(instance, "product_id", None) or (instance.product.id if getattr(instance, "product", None) else None)

    if not p_id:
        p_id = "unknown"

    return f"products/{p_id}/{color_slug}/{filename}"


class Category(models.Model):
    id = models.SlugField(primary_key=True, max_length=100, blank=True, help_text="Unique Category ID (leave blank to auto-generate)")
    name = models.CharField(max_length=200)

    # Keep URL field for frontend compatibility
    image = models.URLField(max_length=500, blank=True)

    # Actual file upload to Supabase Storage
    image_file = models.ImageField(
        upload_to=category_image_path,
        storage=supabase_storage,
        blank=True,
        null=True,
        help_text="Upload category image (will override the URL above if provided)"
    )

    order = models.PositiveIntegerField(
        default=0,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Category Order (optional)",
        help_text="Order position for Category list (1, 2, 3...) (optional)"
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["order", "id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loaded_db_id = self.id

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.order is None:
            self.order = 0
        if self.id:
            self.id = str(self.id).strip()
            old_id = getattr(self, "_loaded_db_id", None)
            is_rename = bool(old_id and self.id != old_id and Category.objects.filter(id=old_id).exists())
            is_new = not old_id and (not self.pk or not Category.objects.filter(pk=self.pk).exists())

            if (is_new or is_rename) and is_id_used(self.id, exclude_category_pk=old_id if is_rename else None):
                raise ValidationError({
                    "id": f"Category ID '{self.id}' is already in use or was assigned to a deleted category. Leave ID blank to auto-generate a unique ID."
                })

    def save(self, *args, **kwargs):
        if self.order is None:
            self.order = 0
        old_id = getattr(self, "_loaded_db_id", None)
        new_id = str(self.id).strip() if self.id else ""

        if old_id and new_id and old_id != new_id and Category.objects.filter(id=old_id).exists():
            if is_id_used(new_id, exclude_category_pk=old_id):
                raise ValidationError({
                    "id": f"Cannot rename Category ID to '{new_id}' because that ID is already assigned to another category or deleted record."
                })

            with transaction.atomic():
                Product.objects.filter(category_id=old_id).update(category_id=new_id)

                if self.image_file and self.image_file.name and f"categories/{old_id}/" in self.image_file.name:
                    self.image_file.name = self.image_file.name.replace(f"categories/{old_id}/", f"categories/{new_id}/")

                Category.objects.filter(id=old_id).update(id=new_id)
                record_used_id("category", new_id)

                try:
                    supabase_storage.move_folder(f"categories/{old_id}", f"categories/{new_id}")
                except Exception as e:
                    print(f"Supabase storage category move_folder warning: {e}")

                self.id = new_id
                self._loaded_db_id = new_id
                super().save(*args, **kwargs)

        else:
            with transaction.atomic():
                if not self.id or not str(self.id).strip():
                    seq, _ = CategoryIDSequence.objects.select_for_update().get_or_create(id=1)
                    while True:
                        seq.last_number += 1
                        candidate = str(seq.last_number)
                        if not is_id_used(candidate):
                            self.id = candidate
                            seq.save()
                            break
                else:
                    self.id = str(self.id).strip()
                    if self.id.isdigit():
                        num = int(self.id)
                        seq, _ = CategoryIDSequence.objects.select_for_update().get_or_create(id=1)
                        if num > seq.last_number:
                            seq.last_number = num
                            seq.save()

                record_used_id("category", self.id)
                super().save(*args, **kwargs)
                self._loaded_db_id = self.id

    def get_image_url(self):
        """Prefer uploaded file, fallback to URL"""
        if self.image_file:
            return self.image_file.url
        return self.image or ""


class Product(models.Model):
    id = models.CharField(primary_key=True, max_length=50, blank=True, help_text="Unique Product ID (leave blank to auto-generate, e.g. 1-3)")
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=150, default="Silk & Loom")

    # Main image – URL + file upload
    image = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Main image URL (fallback) (optional)",
        help_text="Main image URL (fallback) (optional)"
    )
    image_file = models.ImageField(
        upload_to=product_main_image_path,
        storage=supabase_storage,
        blank=True,
        null=True,
        verbose_name="Upload main product image (optional)",
        help_text="Upload main product image (optional)"
    )

    # Gallery – JSON list of URLs for backwards compatibility
    images = models.JSONField(
        default=list,
        blank=True,
        help_text='List of image/video URLs, e.g. ["url1", "url2"]'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        to_field="id",
    )
    description = models.TextField(blank=True)

    # Legacy Variants – JSON for backwards compatibility
    variants = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"color": "Royal Blue", "id": "p1"}, ...]'
    )

    is_new_arrival = models.BooleanField(default=False, db_index=True)
    new_arrival_order = models.PositiveIntegerField(
        default=0,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="New Arrival Order (optional)",
        help_text="Order position for New Arrivals (1, 2, 3...) (optional)"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["new_arrival_order", "-created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loaded_db_id = self.id

    def __str__(self):
        return f"{self.name} ({self.id})"

    def clean(self):
        super().clean()
        if self.new_arrival_order is None:
            self.new_arrival_order = 0
        if self.id:
            self.id = str(self.id).strip()
            old_id = getattr(self, "_loaded_db_id", None)
            is_rename = bool(old_id and self.id != old_id and Product.objects.filter(id=old_id).exists())
            is_new = not old_id and (not self.pk or not Product.objects.filter(pk=self.pk).exists())

            if (is_new or is_rename) and is_id_used(self.id, exclude_product_pk=old_id if is_rename else None):
                raise ValidationError({
                    "id": f"Product ID '{self.id}' is already in use or was assigned to a deleted product. Leave ID blank to auto-generate a unique ID."
                })

    def save(self, *args, **kwargs):
        if self.new_arrival_order is None:
            self.new_arrival_order = 0
        old_id = getattr(self, "_loaded_db_id", None)
        new_id = str(self.id).strip() if self.id else ""

        if old_id and new_id and old_id != new_id and Product.objects.filter(id=old_id).exists():
            if is_id_used(new_id, exclude_product_pk=old_id):
                raise ValidationError({
                    "id": f"Cannot rename Product ID to '{new_id}' because that ID is already assigned to another product or deleted record."
                })

            with transaction.atomic():
                ProductVariantItem.objects.filter(product_id=old_id).update(product_id=new_id)
                ProductGalleryItem.objects.filter(product_id=old_id).update(product_id=new_id)
                WishlistItem.objects.filter(product_id=old_id).update(product_id=new_id)
                ContactLog.objects.filter(product_id=old_id).update(product_id=new_id)

                for v in ProductVariantItem.objects.filter(product_id=new_id):
                    if v.image_file and v.image_file.name and f"products/{old_id}/" in v.image_file.name:
                        v.image_file.name = v.image_file.name.replace(f"products/{old_id}/", f"products/{new_id}/")
                        v.save(update_fields=["image_file"])

                for g in ProductGalleryItem.objects.filter(product_id=new_id):
                    if g.image_file and g.image_file.name and f"products/{old_id}/" in g.image_file.name:
                        g.image_file.name = g.image_file.name.replace(f"products/{old_id}/", f"products/{new_id}/")
                        g.save(update_fields=["image_file"])

                if self.image_file and self.image_file.name and f"products/{old_id}/" in self.image_file.name:
                    self.image_file.name = self.image_file.name.replace(f"products/{old_id}/", f"products/{new_id}/")

                Product.objects.filter(id=old_id).update(id=new_id)
                record_used_id("product", new_id)

                try:
                    supabase_storage.move_folder(f"products/{old_id}", f"products/{new_id}")
                except Exception as e:
                    print(f"Supabase storage product move_folder warning: {e}")

                self.id = new_id
                self._loaded_db_id = new_id
                super().save(*args, **kwargs)

        else:
            with transaction.atomic():
                if not self.id or not str(self.id).strip():
                    if not self.category_id:
                        raise ValidationError("Product must have a category assigned to generate a product ID.")

                    cat_id_prefix = str(self.category_id).strip()
                    seq, _ = ProductIDSequence.objects.select_for_update().get_or_create(category_id=self.category_id)

                    while True:
                        seq.last_number += 1
                        candidate = f"{cat_id_prefix}-{seq.last_number}"
                        if not is_id_used(candidate):
                            self.id = candidate
                            seq.save()
                            break
                else:
                    self.id = str(self.id).strip()
                    if self.category_id:
                        cat_id_prefix = str(self.category_id).strip()
                        pattern = rf"^{re.escape(cat_id_prefix)}-(\d+)$"
                        m = re.match(pattern, self.id)
                        if m:
                            num = int(m.group(1))
                            seq, _ = ProductIDSequence.objects.select_for_update().get_or_create(category_id=self.category_id)
                            if num > seq.last_number:
                                seq.last_number = num
                                seq.save()

                record_used_id("product", self.id)
                super().save(*args, **kwargs)
                self._loaded_db_id = self.id

            # Auto-ensure at least one variant is set as main variant if variants exist
            v_items = list(self.variant_items.all())
            if v_items and not any(v.is_main for v in v_items):
                first_v = v_items[0]
                first_v.is_main = True
                first_v.save(update_fields=["is_main"])

    def get_main_image_url(self):
        v_items = list(self.variant_items.all())
        main_variant = next((v for v in v_items if v.is_main), None)
        if main_variant and main_variant.get_image_url():
            return main_variant.get_image_url()
        if self.image_file:
            return self.image_file.url
        if self.image:
            return self.image
        if v_items:
            return v_items[0].get_image_url()
        return ""

    def get_all_images(self):
        urls = []
        v_items = list(self.variant_items.all())

        main_var = next((v for v in v_items if v.is_main), None)
        if main_var and main_var.get_image_url():
            urls.append(main_var.get_image_url())

        main_prod_url = self.get_main_image_url()
        if main_prod_url and main_prod_url not in urls:
            urls.append(main_prod_url)

        if self.images and isinstance(self.images, list):
            for img in self.images:
                if img and img not in urls:
                    urls.append(img)

        for item in self.gallery_items.all():
            url = item.get_image_url()
            if url and url not in urls:
                urls.append(url)

        for vitem in v_items:
            vurl = vitem.get_image_url()
            if vurl and vurl not in urls:
                urls.append(vurl)

        return urls

    def get_all_variants(self):
        variants_list = []
        seen_colors = set()

        items = list(self.variant_items.order_by('-is_main', 'id'))

        # Rule: If no variant has is_main=True, default top/first variant as main
        if items and not any(v.is_main for v in items):
            items[0].is_main = True

        for item in items:
            color_key = (item.color or "").strip().lower()
            if color_key and color_key in seen_colors:
                continue
            if color_key:
                seen_colors.add(color_key)

            main_url = item.get_image_url()
            specific_gallery = [g.get_image_url() for g in item.gallery_items.all() if g.get_image_url()]

            variant_images = []
            if main_url:
                variant_images.append(main_url)
            for gurl in specific_gallery:
                if gurl not in variant_images:
                    variant_images.append(gurl)

            variants_list.append({
                "id": str(item.id),
                "color": item.color,
                "is_main": item.is_main,
                "image": main_url,
                "images": variant_images
            })

        if self.variants and isinstance(self.variants, list):
            for v in self.variants:
                if isinstance(v, dict) and v.get("color"):
                    ckey = str(v.get("color")).strip().lower()
                    if ckey not in seen_colors:
                        seen_colors.add(ckey)
                        v_copy = dict(v)
                        if "images" not in v_copy:
                            v_copy["images"] = [v_copy.get("image")] if v_copy.get("image") else []
                        variants_list.append(v_copy)

        return variants_list


class NewArrivalProduct(Product):
    class Meta:
        proxy = True
        verbose_name = "New Arrival Product"
        verbose_name_plural = "New Arrivals (Reorder)"


class ProductVariantItem(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variant_items"
    )
    color = models.CharField(max_length=100, help_text="Color name, e.g. Royal Blue")
    is_main = models.BooleanField(
        default=False,
        verbose_name="Is Main Product Variant / Gallery",
        help_text="Turn ON to make this variant the main photo & gallery for the product"
    )
    image = models.URLField(max_length=500, blank=True, verbose_name="Variant main image URL (fallback) (optional)", help_text="Variant main image URL (fallback) (optional)")
    image_file = models.ImageField(
        upload_to=product_variant_image_path,
        storage=supabase_storage,
        blank=True,
        null=True,
        verbose_name="Upload main image for this variant/color (optional)",
        help_text="Upload main image for this variant/color from local system (stores in Supabase Storage) (optional)"
    )

    class Meta:
        verbose_name = "Product Color / Variant"
        verbose_name_plural = "Product Colors / Variants"

    def __str__(self):
        return f"{self.product.name} - {self.color}"

    def get_image_url(self):
        if self.image_file:
            return self.image_file.url
        return self.image or ""

    def get_gallery_images(self):
        urls = []
        main_url = self.get_image_url()
        if main_url:
            urls.append(main_url)
        for item in self.gallery_items.all():
            url = item.get_image_url()
            if url and url not in urls:
                urls.append(url)
        return urls


class ProductGalleryItem(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="gallery_items"
    )
    variant = models.ForeignKey(
        ProductVariantItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="gallery_items",
        help_text="Select specific variant/color for this gallery image (optional)"
    )
    image = models.URLField(max_length=500, blank=True, verbose_name="Gallery image URL (fallback) (optional)", help_text="Gallery image URL (fallback) (optional)")
    image_file = models.ImageField(
        upload_to=product_gallery_path,
        storage=supabase_storage,
        blank=True,
        null=True,
        verbose_name="Upload gallery image file (optional)",
        help_text="Upload gallery image file from local system (stores in Supabase Storage) (optional)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Gallery Image File"
        verbose_name_plural = "Gallery Image Files"

    def __str__(self):
        target = f"{self.product.name}"
        if self.variant:
            target += f" ({self.variant.color})"
        return f"Gallery Image for {target}"

    def get_image_url(self):
        if self.image_file:
            return self.image_file.url
        return self.image or ""


class WishlistItem(models.Model):
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="wishlist_items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="wishlisted_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created_at"]
        verbose_name = "Wishlist Item"
        verbose_name_plural = "Wishlist Items"

    def __str__(self):
        return f"{self.user.email} → {self.product.name}"


class ContactLog(models.Model):
    """
    Logs every successful "Contact Now" click.
    """
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_logs",
        help_text="Authenticated user (null = Guest)"
    )
    guest_name = models.CharField(max_length=150, blank=True)
    guest_mobile = models.CharField(max_length=15, blank=True)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="contact_logs"
    )

    is_demo = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Is Demo Contact Log",
        help_text="True if generated by a demo user or test interaction."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Now Log"
        verbose_name_plural = "Contact Now Logs"

    def __str__(self):
        who = self.user.email if self.user else (self.guest_name or "Guest")
        demo_tag = " [DEMO]" if self.is_demo else ""
        return f"{who}{demo_tag} → {self.product.name} ({self.created_at:%Y-%m-%d %H:%M})"

    def save(self, *args, **kwargs):
        from accounts.models import is_demo_user
        if self.user and is_demo_user(self.user):
            self.is_demo = True
        elif self.guest_name and "demo" in self.guest_name.lower():
            self.is_demo = True
        super().save(*args, **kwargs)

    @property
    def is_guest(self):
        return self.user is None


@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=ProductVariantItem)
@receiver([post_save, post_delete], sender=ProductGalleryItem)
def clear_catalog_cache(sender, **kwargs):
    try:
        cache.clear()
    except Exception:
        pass


@receiver(post_delete, sender=Category)
def delete_category_supabase_folder(sender, instance, **kwargs):
    """
    When a Category is deleted, delete its image file and folder `categories/{category.id}` in Supabase,
    and remove its historical ID record so it can be reused.
    """
    try:
        if instance.id:
            HistoricalUsedID.objects.filter(used_id=str(instance.id).strip()).delete()
    except Exception as e:
        print(f"Error deleting historical category ID for {instance.id}: {e}")

    try:
        if instance.image_file and instance.image_file.name:
            supabase_storage.delete(instance.image_file.name)
        folder = f"categories/{instance.id}"
        supabase_storage.delete_folder(folder)
    except Exception as e:
        print(f"Error deleting category storage files for {instance.id}: {e}")


@receiver(post_delete, sender=Product)
def delete_product_supabase_folder(sender, instance, **kwargs):
    """
    When a Product is deleted, delete all associated image files and folder `products/{product.id}` in Supabase,
    and remove its historical ID record so it can be reused.
    """
    try:
        if instance.id:
            HistoricalUsedID.objects.filter(used_id=str(instance.id).strip()).delete()
    except Exception as e:
        print(f"Error deleting historical product ID for {instance.id}: {e}")

    try:
        if instance.image_file and instance.image_file.name:
            supabase_storage.delete(instance.image_file.name)
        folder = f"products/{instance.id}"
        supabase_storage.delete_folder(folder)
    except Exception as e:
        print(f"Error deleting product storage files for {instance.id}: {e}")


@receiver(post_delete, sender=ProductVariantItem)
def delete_variant_supabase_image(sender, instance, **kwargs):
    """
    When a ProductVariantItem is deleted, delete its image file from Supabase.
    """
    try:
        if instance.image_file and instance.image_file.name:
            supabase_storage.delete(instance.image_file.name)
    except Exception as e:
        print(f"Error deleting variant image file for {instance.id}: {e}")


@receiver(post_delete, sender=ProductGalleryItem)
def delete_gallery_item_supabase_image(sender, instance, **kwargs):
    """
    When a ProductGalleryItem is deleted, delete its image file from Supabase.
    """
    try:
        if instance.image_file and instance.image_file.name:
            supabase_storage.delete(instance.image_file.name)
    except Exception as e:
        print(f"Error deleting gallery image file for {instance.id}: {e}")


def showcase_image_path(instance, filename):
    return f"showcase/{filename}"


class GadwalWeavingShowcase(models.Model):
    heading = models.CharField(
        max_length=255, 
        default="The Art of Gadwal Weaving",
        help_text="Main heading title for the showcase section"
    )
    description = models.TextField(
        default="Discover our exquisite collection of Gadwal sarees, where traditional craftsmanship meets timeless elegance. Woven with rich heritage and intricate detailing, each saree reflects the beauty of simplicity, tradition, and enduring style.",
        help_text="Detailed description paragraph"
    )
    button_text = models.CharField(
        max_length=100, 
        default="VIEW THE COLLECTION",
        help_text="Text to display on the action button"
    )
    button_link = models.CharField(
        max_length=255, 
        default="/products", 
        blank=True,
        help_text="URL or route path for the button link (e.g., /products)"
    )
    is_active = models.BooleanField(
        default=True, 
        help_text="Toggle to show or hide this showcase section on the home page"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Weaving Showcase Section"
        verbose_name_plural = "Weaving Showcase Section"

    def __str__(self):
        return self.heading or "Weaving Showcase"


class GadwalWeavingImage(models.Model):
    showcase = models.ForeignKey(
        GadwalWeavingShowcase, 
        on_delete=models.CASCADE, 
        related_name="images"
    )
    image_file = models.ImageField(
        upload_to=showcase_image_path, 
        storage=supabase_storage, 
        blank=True, 
        null=True,
        help_text="Upload image file"
    )
    image_url = models.CharField(
        max_length=500, 
        blank=True, 
        help_text="Or paste image URL directly"
    )
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order sequence (0, 1, 2...)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Showcase Image"
        verbose_name_plural = "Showcase Images"

    def get_image_url(self):
        if self.image_file and hasattr(self.image_file, "url"):
            try:
                return self.image_file.url
            except Exception:
                pass
        if self.image_url:
            return self.image_url
        return ""

    def __str__(self):
        return f"Image #{self.order} - {self.caption or self.id}"


@receiver(post_delete, sender=GadwalWeavingImage)
def delete_showcase_image_file(sender, instance, **kwargs):
    try:
        if instance.image_file and instance.image_file.name:
            supabase_storage.delete(instance.image_file.name)
    except Exception as e:
        print(f"Error deleting showcase image file: {e}")

