from django.urls import path
from . import views

urlpatterns = [
    path('', views.VitalsIngestionView.as_view(), name='vitals-ingest'),
    path('live/<str:user_id>/', views.LiveVitalsView.as_view(), name='vitals-live'),
    path('risk-results/', views.RiskResultIngestionView.as_view(), name='risk-results-ingest'),
]