from django.urls import path
from .views import (
    CategoryListView,
    ProductListView,
    ProductDetailView,
    WishlistListView,
    WishlistToggleView,
    ContactProductView,
    ReorderNewArrivalsView,
    ReorderCategoriesView,
    GadwalWeavingShowcaseView,
    CheckIDAvailabilityView,
)

urlpatterns = [
    path("check-id/", CheckIDAvailabilityView.as_view(), name="check-id-availability"),
    path("categories/reorder/", ReorderCategoriesView.as_view(), name="reorder-categories"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("showcase/", GadwalWeavingShowcaseView.as_view(), name="gadwal-weaving-showcase"),

    # Specific routes must come BEFORE the dynamic <str:id> route
    path("products/reorder_new_arrivals/", ReorderNewArrivalsView.as_view(), name="reorder-new-arrivals"),
    path("products/contact/", ContactProductView.as_view(), name="product-contact"),
    path("wishlist/", WishlistListView.as_view(), name="wishlist-list"),
    path("wishlist/<str:product_id>/", WishlistToggleView.as_view(), name="wishlist-toggle"),

    # Dynamic route last
    path("products/<str:id>/", ProductDetailView.as_view(), name="product-detail"),
]

