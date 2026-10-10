from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "image", "order"]

    def get_image(self, obj):
        return obj.get_image_url()


class ProductListSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field="id",
        read_only=True
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    isNewArrival = serializers.BooleanField(source="is_new_arrival")
    image = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "brand",
            "image", "images", "variants", "category", "description",
            "createdAt", "isNewArrival",
        ]

    def get_image(self, obj):
        return obj.get_main_image_url()

    def get_images(self, obj):
        main_url = obj.get_main_image_url()
        urls = [main_url] if main_url else []
        if isinstance(obj.images, list):
            for img in obj.images:
                if img and img not in urls:
                    urls.append(img)
        return urls

    def get_variants(self, obj):
        variants_list = []
        seen_colors = set()

        v_items = list(obj.variant_items.all())
        if v_items:
            for item in v_items:
                color_key = (item.color or "").strip().lower()
                if color_key and color_key in seen_colors:
                    continue
                if color_key:
                    seen_colors.add(color_key)

                v_url = item.get_image_url() or obj.get_main_image_url()
                variants_list.append({
                    "id": str(item.id),
                    "color": item.color,
                    "image": v_url,
                    "is_main": item.is_main,
                })
        elif isinstance(obj.variants, list):
            for v in obj.variants:
                if isinstance(v, dict):
                    color_name = v.get("color", "")
                    color_key = color_name.strip().lower()
                    if color_key and color_key not in seen_colors:
                        seen_colors.add(color_key)
                        variants_list.append({
                            "id": v.get("id"),
                            "color": color_name,
                            "image": v.get("image") or obj.get_main_image_url(),
                            "is_main": v.get("is_main", False),
                        })

        return variants_list


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field="id",
        read_only=True
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    isNewArrival = serializers.BooleanField(source="is_new_arrival")
    image = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "brand",
            "image", "images",
            "category", "description", "variants",
            "createdAt", "isNewArrival",
        ]

    def get_image(self, obj):
        return obj.get_main_image_url()

    def get_images(self, obj):
        return obj.get_all_images()

    def get_variants(self, obj):
        return obj.get_all_variants()




from .models import Category, Product, WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    # Return the full product object (same shape the frontend expects)
    product = ProductSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "product", "created_at"]


class ContactProductSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    # Optional – useful for guests
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    mobile = serializers.CharField(max_length=15, required=False, allow_blank=True)


from .models import GadwalWeavingShowcase, GadwalWeavingImage

class GadwalWeavingImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = GadwalWeavingImage
        fields = ["id", "image", "caption", "order"]

    def get_image(self, obj):
        return obj.get_image_url()


class GadwalWeavingShowcaseSerializer(serializers.ModelSerializer):
    images = GadwalWeavingImageSerializer(many=True, read_only=True)

    class Meta:
        model = GadwalWeavingShowcase
        fields = ["id", "heading", "description", "button_text", "button_link", "is_active", "images"]