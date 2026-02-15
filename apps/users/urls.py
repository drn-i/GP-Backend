from django.urls import path
from . import views

urlpatterns = [
    path('sync/', views.UserSyncView.as_view(), name='user-sync'),
]