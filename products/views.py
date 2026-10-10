from django.shortcuts import render

# Create your views here.
from rest_framework import generics, status


from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .models import Category, Product, WishlistItem, ContactLog
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductListSerializer,
    WishlistItemSerializer,
    ContactProductSerializer,
)

from urllib.parse import quote
from django.conf import settings


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all().order_by("order", "id")
    serializer_class = CategorySerializer


from rest_framework.pagination import PageNumberPagination
from django.db import models


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "current_page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })


class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = Product.objects.select_related("category").prefetch_related("variant_items", "variant_items__gallery_items", "gallery_items").all()

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category_id=category)

        is_new = self.request.query_params.get("isNewArrival")
        if is_new is not None:
            if is_new.lower() in ("true", "1", "yes"):
                qs = qs.filter(is_new_arrival=True).order_by("new_arrival_order", "-created_at")
                return qs
            elif is_new.lower() in ("false", "0", "no"):
                qs = qs.filter(is_new_arrival=False)

        sort = self.request.query_params.get("sort", "-createdAt")
        if sort in ("createdAt", "-createdAt", "-created_at", "created_at"):
            field = "created_at" if sort in ("createdAt", "created_at") else "-created_at"
            qs = qs.order_by(field)
        elif sort == "name_asc":
            qs = qs.order_by("name")
        elif sort == "name_desc":
            qs = qs.order_by("-name")
        else:
            qs = qs.order_by("-created_at")

        search = self.request.query_params.get("search") or self.request.query_params.get("q")
        if search:
            qs = qs.filter(
                models.Q(name__icontains=search) |
                models.Q(description__icontains=search) |
                models.Q(brand__icontains=search)
            )

        return qs


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.select_related("category").prefetch_related(
        "variant_items",
        "variant_items__gallery_items",
        "gallery_items"
    ).all()
    serializer_class = ProductSerializer
    lookup_field = "id"




class WishlistListView(APIView):
    """
    GET /api/wishlist/
    Returns the list of products in the current user's wishlist.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = WishlistItem.objects.filter(user=request.user).select_related("product", "product__category")
        # Return just the product objects so the frontend can use them directly
        products = [item.product for item in items]
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class WishlistToggleView(APIView):
    """
    POST   /api/wishlist/<product_id>/   → add
    DELETE /api/wishlist/<product_id>/   → remove
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
        if created:
            return Response(
                {"message": "Added to wishlist.", "product": ProductSerializer(product).data},
                status=status.HTTP_201_CREATED,
            )
        return Response({"message": "Already in wishlist."}, status=status.HTTP_200_OK)

    def delete(self, request, product_id):
        deleted, _ = WishlistItem.objects.filter(user=request.user, product_id=product_id).delete()
        if deleted:
            return Response({"message": "Removed from wishlist."}, status=status.HTTP_200_OK)
        return Response({"error": "Item not found in wishlist."}, status=status.HTTP_404_NOT_FOUND)





class ContactProductView(APIView):
    """
    POST /api/products/contact/
    Generates WhatsApp link + logs the click (Authenticated or Guest).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ContactProductSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product_id = serializer.validated_data["product_id"]
        guest_name = serializer.validated_data.get("name", "").strip()
        guest_mobile = serializer.validated_data.get("mobile", "").strip()

        try:
            product = Product.objects.select_related("category").get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        # ----- Log the click -----
        user = request.user if request.user.is_authenticated else None

        ContactLog.objects.create(
            user=user,
            guest_name=guest_name if not user else "",
            guest_mobile=guest_mobile if not user else "",
            product=product,
        )

        # ----- Build WhatsApp message -----
        message_lines = [
            "Hello, I am interested in this product:",
            "",
            f"Product  : {product.name}",
            f"Brand    : {product.brand}",
            f"Category : {product.category.name}",
            f"ID       : {product.id}",
            "",
            "Please share more details. Thank you!",
        ]
        message = "\n".join(message_lines)

        whatsapp_number = getattr(settings, "WHATSAPP_NUMBER", "919999999999")
        encoded_message = quote(message)
        whatsapp_url = f"https://web.whatsapp.com/send?phone={whatsapp_number}&text={encoded_message}"

        return Response({
            "success": True,
            "whatsapp_number": whatsapp_number,
            "message": message,
            "whatsapp_url": whatsapp_url,
        })


class ReorderNewArrivalsView(APIView):
    """
    POST /api/products/reorder_new_arrivals/
    Body: { "product_ids": ["3-1", "2-2", "21", "1-2", "1-1"] }
    Updates `new_arrival_order` for each product in the specified order.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        product_ids = request.data.get("product_ids", [])
        if not isinstance(product_ids, list):
            return Response({"error": "product_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        for index, prod_id in enumerate(product_ids, start=1):
            Product.objects.filter(id=str(prod_id)).update(new_arrival_order=index)

        try:
            from django.core.cache import cache
            cache.clear()
        except Exception:
            pass

        return Response({"success": True, "message": f"Successfully updated order for {len(product_ids)} products."})


class ReorderCategoriesView(APIView):
    """
    POST /api/categories/reorder/
    Body: { "category_ids": ["1", "2", "3"] }
    Updates `order` for each category in the specified order.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        category_ids = request.data.get("category_ids", [])
        if not isinstance(category_ids, list):
            return Response({"error": "category_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        for index, cat_id in enumerate(category_ids, start=1):
            Category.objects.filter(id=str(cat_id)).update(order=index)

        try:
            from django.core.cache import cache
            cache.clear()
        except Exception:
            pass

        return Response({"success": True, "message": f"Successfully updated order for {len(category_ids)} categories."})


from .models import GadwalWeavingShowcase, is_id_used
from .serializers import GadwalWeavingShowcaseSerializer

class GadwalWeavingShowcaseView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        showcase = GadwalWeavingShowcase.objects.filter(is_active=True).first()
        if not showcase:
            showcase = GadwalWeavingShowcase.objects.create(
                heading="The Art of Handloom Weaving",
                description="Discover our exquisite collection of handloom sarees, where traditional craftsmanship meets timeless elegance. Woven with rich heritage and intricate detailing, each saree reflects the beauty of simplicity, tradition, and enduring style.",
                button_text="VIEW THE COLLECTION",
                button_link="/products",
                is_active=True
            )
        serializer = GadwalWeavingShowcaseSerializer(showcase, context={"request": request})
        return Response(serializer.data)


class CheckIDAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        used_id = request.query_params.get("id", "").strip()
        id_type = request.query_params.get("type", "product").strip().lower()
        exclude_pk = request.query_params.get("exclude_pk", "").strip()

        if not used_id:
            return Response({"available": True, "message": "ID will be auto-generated"})

        exclude_cat = exclude_pk if id_type == "category" and exclude_pk else None
        exclude_prod = exclude_pk if id_type == "product" and exclude_pk else None

        used = is_id_used(used_id, exclude_category_pk=exclude_cat, exclude_product_pk=exclude_prod)
        return Response({
            "available": not used,
            "id": used_id,
            "message": f"{id_type.capitalize()} ID '{used_id}' is already in use" if used else "ID is available"
        })


