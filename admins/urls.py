from django.urls import path
from .views import DashboardOverview, UserListView,\
    EarningsListView, AdminNotificationView

urlpatterns = [
    path('dashboard-overview/', DashboardOverview.as_view(), name='dashboard-overview'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('earnings/', EarningsListView.as_view(), name='earnings-list'),
    path('notifications/', AdminNotificationView.as_view(), name='notifications'),
    path("notifications/<int:pk>/", AdminNotificationView.as_view(), name="notification-update"),
]
