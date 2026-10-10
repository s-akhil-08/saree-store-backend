from django.urls import path
from .views import ConsultationCreateView, ConsultationListView

urlpatterns = [
    path("consultations/", ConsultationCreateView.as_view(), name="consultation-create"),
    path("consultations/list/", ConsultationListView.as_view(), name="consultation-list"),
]