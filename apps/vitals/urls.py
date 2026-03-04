from django.urls import path
from . import views

urlpatterns = [
    path('', views.VitalsIngestionView.as_view(), name='vitals-ingest'),
    path('live/<str:user_id>/', views.LiveVitalsView.as_view(), name='vitals-live'),
    path('risk-results/', views.RiskResultIngestionView.as_view(), name='risk-results-ingest'),
    path('risk-results/<str:user_id>/', views.RiskSummaryView.as_view(), name='risk-results-summary'),
    path('risk-events/', views.AllRiskEventsView.as_view(), name='all-risk-events'),
    path('dashboard/<str:user_id>/', views.MobileDashboardView.as_view(), name='mobile-dashboard'),
]