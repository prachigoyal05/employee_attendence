from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .models import Attendance
from .models import DeviceLog #ip

# --------custom user------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Display fields in admin list view
    list_display = ('username', 'email', 'role', 'contact', 'department', 'is_active', 'is_staff')

    # Add filtering options
    list_filter = ('role', 'is_staff', 'is_superuser', 'department')

    # Organize fields shown in the user edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Employee Details', {
            'fields': ('role', 'is_email_verified', 'contact', 'address', 'joining_date', 'department')
        }),
    )

    # Fields when adding a new user from admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Employee Details', {
            'fields': ('role', 'contact', 'address', 'joining_date', 'department')
        }),
    )

    # Optional: Search by these fields in admin
    search_fields = ('username', 'email', 'contact', 'department')

# enhance admin for attendence----------
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'date',
        'check_in',
        'checkout',
        'status',
        'total_break_duration',
        'total_work_duration',
        'on_break',
    )
    list_filter = ('date', 'status')
    search_fields = ('user__username', 'user__email', 'date')

# --------device log-----
@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display  = (
        "user",
        "ip_address",
        "device_type",
        "browser",
        "os",
        "first_seen",
        "last_seen",
    )
    list_filter   = ("device_type", "browser", "os")
    search_fields = ("ip_address", "user__username", "browser", "os")
    date_hierarchy = "first_seen"        # adds sidebar date drill‑down
    readonly_fields = ("first_seen", "last_seen")

    ordering = ("-last_seen",)