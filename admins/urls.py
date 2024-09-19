from django.urls import path
from .views import DashboardOverview, UserListView

urlpatterns = [
    path('dashboard-overview/', DashboardOverview.as_view(), name='dashboard-overview'),
    path('users/', UserListView.as_view(), name='user-list'),

]
