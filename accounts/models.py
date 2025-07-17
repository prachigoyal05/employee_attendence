# accounts\models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('employee', 'Employee'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')
    is_email_verified = models.BooleanField(default=False)

    contact = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

#for employee dashboard
#attendence-check in check out
User = get_user_model()

class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    check_in = models.DateTimeField(null=True, blank=True)
    checkout = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='Absent')  # Present, Absent, Partial, Checked Out
    total_work_duration = models.DurationField(null=True, blank=True)
    total_break_duration = models.DurationField(default=timezone.timedelta)
    on_break = models.BooleanField(default=False)
    break_start = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.status}"
    

# break session model
class BreakSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

# dailybreakstatus model
class DailyBreakStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    total_break_used = models.DurationField(default=timedelta)
    remaining_break_time = models.DurationField(default=timedelta(hours=1, minutes=30))  # 1.5 hrs max

# device log model- for implementing ips
class DeviceLog(models.Model):
    user        = models.ForeignKey(get_user_model(),
                                    on_delete=models.CASCADE,
                                    related_name="device_logs")
    session_key = models.CharField(max_length=40, db_index=True)
    ip_address  = models.GenericIPAddressField()
    user_agent  = models.TextField()
    device_type = models.CharField(max_length=20)   # mobile / desktop / tablet
    browser     = models.CharField(max_length=50)
    os          = models.CharField(max_length=50)
    mac_address = models.CharField(max_length=17, blank=True, null=True)
    first_seen  = models.DateTimeField(auto_now_add=True)
    last_seen   = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} @ {self.ip_address} [{self.device_type}]"