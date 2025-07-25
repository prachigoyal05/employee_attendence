# accounts/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils.cache import add_never_cache_headers
from ipware import get_client_ip #for ip
from .models import DeviceLog

class NoCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        add_never_cache_headers(response)
        return response


# 1)  ADMIN‑ONLY PAGES

class AdminAccessMiddleware:
    """Block non‑admins from admin‑only URLs."""
    def __init__(self, get_response):
        self.get_response = get_response
        self.protected = [
            '/accounts/admin-dashboard/',
            '/accounts/employees/edit/',
            '/accounts/employees/delete/',
        ]

    def __call__(self, request):
        path = request.path
        if any(path.startswith(p) for p in self.protected):
            if not request.user.is_authenticated:
                return redirect('login')
            if getattr(request.user, "role", "") != "admin":
                return redirect('employee_dashboard')
        return self.get_response(request)


# 2)  EMPLOYEE‑ONLY PAGES
class EmployeeAccessMiddleware:
    """Block admins / anonymous users from employee‑only URLs."""
    def __init__(self, get_response):
        self.get_response = get_response
        self.employee_paths = [
            '/accounts/employee-dashboard/',
            '/accounts/attendance/mark/',
            '/accounts/attendance/start-break/',
            '/accounts/attendance/end-break/',
            '/accounts/attendance/checkout/',
        ]

    def __call__(self, request):
        if any(request.path.startswith(p) for p in self.employee_paths):
            if not request.user.is_authenticated:
                return redirect('login')
            if getattr(request.user, "role", "") != "employee":
                return redirect('admin_dashboard')
        return self.get_response(request)


# 3)  NO‑CACHE MIDDLEWARE
class NoCacheMiddleware(MiddlewareMixin):
    """
    Prevent browser / proxy caching so a user cannot return to a protected
    dashboard page with the back‑button after logout.
    """
    def process_response(self, request, response):
        add_never_cache_headers(response)
        return response

# ip
class LogDeviceMiddleware:
    """
    After a successful Django login, store or update a DeviceLog record.
    Add *below* AuthenticationMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            # 1️⃣  IP
            ip, _ = get_client_ip(request)
            ip = ip or "0.0.0.0"

            # 2️⃣  UA details (django-user-agents)
            ua = request.user_agent
            device_type = "mobile" if ua.is_mobile else "tablet" if ua.is_tablet else "desktop"

            # 3️⃣  Session key (helps group multiple requests)
            session_key = request.session.session_key

            # 4️⃣  Upsert
            DeviceLog.objects.update_or_create(
                user=request.user,
                session_key=session_key,
                defaults={
                    "ip_address": ip,
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "device_type": device_type,
                    "browser": f"{ua.browser.family} {ua.browser.version_string}",
                    "os": f"{ua.os.family} {ua.os.version_string}",
                },
            )

        return response
    
    