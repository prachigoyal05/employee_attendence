from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('employees/view/<slug:username>/', views.view_employee, name='view_employee'),
    path('employees/edit/<slug:username>/', views.edit_employee, name='edit_employee'),
    path('employees/delete/<slug:username>/', views.delete_employee, name='delete_employee'),
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html'), name='password_change'),
    # path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('logout/', views.user_logout, name='logout'),
    path('employee-dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('attendance/mark/', views.mark_attendance, name='mark_attendance'),
    path('attendance/start-break/', views.start_break, name='start_break'),
    path('attendance/end-break/', views.end_break, name='end_break'),
    path('attendance/checkout/', views.checkout, name='checkout'), 
    path('dashboard/<str:section>/', views.dashboard_router, name='dashboard_router'),
    path('admin/export-attendance/', views.export_attendance, name='export_attendance'),
    path("admin/device-logs/",  views.device_logs, name="device_logs"),
    ]

