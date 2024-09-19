from django.urls import path
from .views import DashboardOverview

urlpatterns = [
    path('dashboard-overview/', DashboardOverview.as_view(), name='dashboard-overview'),
]
