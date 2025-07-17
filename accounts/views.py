# accounts\views.py
import pandas as pd
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.contrib import messages
from .forms import RegistrationForm
from .models import CustomUser
from django import forms
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from .models import Attendance
from django.utils.timezone import make_aware
from datetime import datetime, time, date
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from .models import Attendance, DailyBreakStatus, BreakSession
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import DeviceLog #ip

@never_cache
def user_login(request):
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('admin_dashboard')
        return redirect('employee_dashboard')
        # User hit /login while already logged‑in → flush & force re‑login
        # logout(request)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)

                  # ── EXPIRE WHEN BROWSER CLOSES ────────────────────────
                request.session.set_expiry(0)        # cookie dies with tab
                request.session.modified = True      # ensure cookie is sent

                if user.role == 'admin':
                    return redirect('admin_dashboard')
                else:
                    return redirect('employee_dashboard')
            else:
                messages.error(request, 'Your email is not verified yet.')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'accounts/login.html')


def home(request):
    return HttpResponse("Welcome to the Employee Attendance System!")


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Email not verified yet
            user.save()

            # Email verification
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = f"http://127.0.0.1:8000/accounts/activate/{uid}/{token}/"

            send_mail(
                'Verify your email',
                f'Click this link to verify your account: {activation_link}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            messages.success(request, 'Check your email to verify your account.')
            return redirect('login')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except Exception:
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.is_email_verified = True
        user.save()

        if user.role == 'admin':
            return redirect('admin_dashboard')
        else:
            return redirect('employee_dashboard')
    else:
        return render(request, 'accounts/activation_failed.html')


#admin dashboard---------------
@never_cache
@login_required(login_url='login')
def admin_dashboard(request):
    if request.user.role != 'admin':
        return redirect('employee_dashboard')
    employees = CustomUser.objects.filter(role='employee')
 
    User = get_user_model()
    context = {
        "users": User.objects.filter(is_active=True).order_by("username"),
        # …any other vars you pass to the template
    }
    # ----- base queryset ----------------------------------
    qs = Attendance.objects.select_related('user').order_by('-date')

    # -------- week filter ---------------------------------
    week_param = request.GET.get('week')        # e.g. '2025-W28'
    if week_param:
        try:
            year_str, week_str = week_param.split('-W')
            year, week = int(year_str), int(week_str)
            qs = qs.filter(date__year=year, date__week=week)
            selected_period = f"Week {week} / {year}"
        except ValueError:
            selected_period = "Invalid week"
    else:
        selected_period = None   # show “Today” later

    if not week_param:
        date_param = request.GET.get('date')
        if date_param:
            try:
                selected_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                selected_date = timezone.now().date()
        else:
            selected_date = timezone.now().date()
        qs = qs.filter(date=selected_date)
    else:
        # still compute selected_date for break duration calculation
        selected_date = timezone.now().date()

    
     # NAME search (param ?q=searchterm)
    query = request.GET.get('q')
    if query:
        qs = qs.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        )

    records = qs
     # Calculate total break duration from BreakSession
    break_data = {}
    for record in records:
        sessions = BreakSession.objects.filter(user=record.user, date=selected_date)
        total = timedelta()
        for session in sessions:
            if session.end_time:
                total += (session.end_time - session.start_time)
        break_data[record.user.id] = total

    #  device log
    device_logs = DeviceLog.objects.select_related('user').order_by('-last_seen')
    
    # ── apply filters ──────────────────────────────────────────
    q      = request.GET.get('q', '')
    start  = request.GET.get('start')
    end    = request.GET.get('end')

    if q:
        device_logs = device_logs.filter(user__username__icontains=q)

    if start and end:
        device_logs = device_logs.filter(first_seen__date__range=[start, end])
    elif start:
        device_logs = device_logs.filter(first_seen__date=start)
        
    return render(request, 'accounts/admin_dashboard.html', {
        'employees': employees,
        'records': records,
        'selected_date': selected_date,
        'selected_period': selected_period,
        'query': query or '',
        'break_data': break_data,
        'device_logs': device_logs,
    })


#for view in admin dashboard
@login_required(login_url='login')
def view_employee(request, username):
    employee = get_object_or_404(CustomUser, username=username)
    return render(request, 'accounts/view_employee.html', {'employee': employee})

#for editing
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'department','contact','address','joining_date']

def edit_employee(request, username):
    employee = get_object_or_404(CustomUser,username=username)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'accounts/edit_employee.html', {'form': form, 'employee': employee})

#for deleting
def delete_employee(request, username):
    employee = get_object_or_404(CustomUser, username=username)
    if request.method == 'POST':
        employee.delete()
        return redirect('admin_dashboard')
    return render(request, 'accounts/delete_employee.html', {'employee': employee})

#for logout
@never_cache
def user_logout(request):
    logout(request)

    response = HttpResponse(
        "<script>sessionStorage.clear();"
        "window.location.href = '/accounts/login/';</script>"
    )
    request.session.flush()  #Clears all session data
    messages.success(request, "You have successfully logged out.")
    return redirect('login')  # Assuming you have a 'login' path
    response.delete_cookie(settings.SESSION_COOKIE_NAME)   # removes cookie in browser
    return response

#employee dashboard--------------------------------
@never_cache
@login_required(login_url='login')
def employee_dashboard(request):
    user = request.user
    if user.role != 'employee':
        return redirect('admin_dashboard')

    today = timezone.now().date()
    current_time = timezone.now().time()

    # Get or create today's attendance
    today_attendance, created = Attendance.objects.get_or_create(user=user, date=today)
    
    break_status, _ = DailyBreakStatus.objects.get_or_create(user=user, date=today)

    break_sessions = BreakSession.objects.filter(user=user, date=today)

    # Fetch all logs of the employee
    logs = Attendance.objects.filter(user=user).order_by('-date')
    
    # Auto mark Absent after 7 PM if no checkout
    if today_attendance.check_in and not today_attendance.checkout and current_time > time(19, 0):
        today_attendance.status = 'Absent'
        today_attendance.save()

    # Logic to show/hide buttons
    can_check_in = not today_attendance.check_in and current_time <= time(11, 30)
    can_check_out = today_attendance.check_in and not today_attendance.checkout and current_time <= time(19, 0)

    # Process status for calendar
    processed_logs = []
    for log in logs:
        status = 'Absent'
        if log.check_in and log.checkout:
            status = 'Present'
        elif log.check_in and not log.checkout:
            if log.date == today and current_time < time(19, 0):  # before 7 PM
                status = 'Pending'
            else:
                status = 'Absent'
        processed_logs.append({
            'date': log.date,
            'status': status,
        })

    return render(request, 'accounts/employee_dashboard.html', {
        'employee': user,
        'today_attendance': today_attendance,
        'logs': processed_logs,
        'can_check_in': can_check_in,
        'can_check_out': can_check_out,
        'remaining_break': break_status.remaining_break_time,
        'break_sessions': break_sessions,
    })

@staff_member_required
@login_required(login_url='login')
def daily_attendance(request):
    today = timezone.now().date()
    records = Attendance.objects.filter(date=today).select_related('user')

    return render(request, 'accounts/admin_attendance.html', {
        'records': records,
        'today': today,
    })

@login_required
def mark_attendance(request):
    user = request.user
    now = timezone.now()
    today = now.date()
    cutoff_checkin = time(11, 30)

    attendance, created = Attendance.objects.get_or_create(user=user, date=today)

    if attendance.check_in:
        return JsonResponse({'message': 'Already checked in'})

    if now.time() > cutoff_checkin:
        attendance.status = 'Absent'
        attendance.save()
        return JsonResponse({'message': 'Check-in closed. Marked Absent'})
    else:
        attendance.check_in = now
        attendance.status = 'Present'
        attendance.save()
        return JsonResponse({'message': 'Checked In Successfully'})
    

# Employee attendence logs views
def employee_attendance_log(request):
    user = request.user
    attendance_logs = Attendance.objects.filter(user=user).order_by('-date')
    return render(request, 'accounts/employee_logs.html', {'logs': attendance_logs})

    
# start break view
@login_required
def start_break(request):
    user = request.user
    today = timezone.now().date()
    now = timezone.now()

    # Ensure user has checked in
    attendance, created = Attendance.objects.get_or_create(user=user, date=today)
    if not attendance.check_in:
        return JsonResponse({'error': 'Check in first'}, status=400)

    # Get or create DailyBreakStatus
    break_status, _ = DailyBreakStatus.objects.get_or_create(user=user, date=today)

    # Check if remaining break time is available
    if break_status.remaining_break_time <= timedelta():
        return JsonResponse({'error': 'No break time left for today'}, status=400)

    # Prevent starting another break if already on break
    if attendance.on_break:
        return JsonResponse({'error': 'You are already on break'}, status=400)

    # Create new break session
    BreakSession.objects.create(user=user, date=today, start_time=now)
    attendance.on_break = True
    attendance.break_start = now
    attendance.save()

    return JsonResponse({'message': 'Break started successfully'})

#end break view
@login_required
def end_break(request):
    user = request.user
    today = timezone.now().date()
    now = timezone.now()

    try:
        # Get attendance and status
        attendance = Attendance.objects.get(user=user, date=today)
        break_status = DailyBreakStatus.objects.get(user=user, date=today)

        # Get the last active break session
        break_session = BreakSession.objects.filter(user=user, date=today, end_time__isnull=True).last()
        if not break_session:
            return JsonResponse({'error': 'No break session to end'}, status=400)

        # Calculate break duration
        duration = now - break_session.start_time

        # If over remaining time, limit the duration to remaining time
        if duration > break_status.remaining_break_time:
            duration = break_status.remaining_break_time

        # Update models
        break_session.end_time = break_session.start_time + duration
        break_session.save()

        break_status.total_break_used += duration
        break_status.remaining_break_time -= duration
        break_status.save()

        # Also update attendance total_break_duration
        attendance.total_break_duration += duration
        attendance.on_break = False
        attendance.break_start = None
        attendance.save()

        return JsonResponse({'message': 'Break ended successfully'})

    except (Attendance.DoesNotExist, DailyBreakStatus.DoesNotExist):
        return JsonResponse({'error': 'Required records not found'}, status=400)

# Checkout
@login_required
def checkout(request):
    user = request.user
    if user.role != 'employee':
        return redirect('admin_dashboard')

    today = timezone.now().date()
    now = timezone.localtime()

    try:
        attendance = Attendance.objects.get(user=user, date=today)

        # Prevent checkout after 7:00 PM
        if now.time() > time(19, 0):
            attendance.status = 'Absent'
            attendance.save()
            return redirect('employee_dashboard')

        # Save checkout time
        attendance.checkout = now

        # Calculate total duration
        if attendance.check_in:
            total_duration = now - attendance.check_in  # total time from checkin to now
            break_duration = attendance.total_break_duration or timedelta()
            net_work_duration = total_duration - break_duration

            attendance.total_work_duration = net_work_duration

    # Check 8-hour condition
            if net_work_duration >= timedelta(hours=6):
                attendance.status = 'Present'
            else:
                attendance.status = 'Absent'

        attendance.save()

    except Attendance.DoesNotExist:
        pass

    return redirect('employee_dashboard')


# map “section” → template or other view
SECTION_MAP = {
    "home":             "accounts/partials/home.html",
    "employees":        "accounts/partials/employees.html",
    "daily-attendance": "accounts/partials/daily_attendance.html",
    "reports":          "accounts/partials/reports.html",
    }

@never_cache
@login_required(login_url='login')
def dashboard_router(request, section):
    """
    Serve different dashboard subsections with ONE endpoint.

    /dashboard/home/             -> renders home partial
    /dashboard/employees/        -> renders employees partial
    /dashboard/daily-attendance/ -> renders attendance partial
    …
    """
    # --- authorisation guard (example) -----------------
    if section in ["employees", "reports"] and request.user.role != "admin":
        # non‑admins are not allowed into those sections
        return redirect("employee_dashboard")

    # --- locate template or 404 ------------------------
    template = SECTION_MAP.get(section)
    if not template:
        return render(request, "404.html", status=404)

    context = build_dashboard_context(request, section)
    return render(request, template, context)


def build_dashboard_context(request, section):
    """
    Collect data you need for each section.
    Keeps the router tidy.
    """
    if section == "home":
        return {
            "totals": ...,
            "clock": ...,
        }
    if section == "employees":
        return {
            "employees": CustomUser.objects.filter(role="employee"),
        }
    if section == "daily-attendance":
        today = timezone.now().date()
        records = Attendance.objects.filter(date=today).select_related("user")
        return {
            "selected_date": today,
            "records": records,
        }
    if section == "device-logs":
        logs = DeviceLog.objects.select_related("user").order_by("-last_seen")
        return {"logs": logs}
    # default
    return {}

# CSV/excel import
@staff_member_required
@never_cache
@login_required(login_url='login')
def export_attendance(request):
    if request.GET.get("download") != "1":
        users = CustomUser.objects.filter(is_active=True).order_by("username")
        return render(request, "accounts/export_attendance.html", {"users": users})
    # Filter by optional query parameters
    user_id = request.GET.get('user_id')
    start_date = request.GET.get('start_date')  # Format: YYYY-MM-DD
    end_date = request.GET.get('end_date')

    qs = Attendance.objects.all().select_related("user")

    # 3️⃣  Apply filters
    if user_id:
        qs = qs.filter(user_id=user_id)            # FK column is user_id
    if start_date and end_date:
        qs = qs.filter(date__range=[start_date, end_date])
    elif start_date:                               # allow single‑day export
        qs = qs.filter(date=start_date)

    # 4️⃣  Serialise to a DataFrame
    records = [{
        "User"        : a.user.username,
        "Date"            : a.date.isoformat(),
        "Check_in"        : a.check_in.strftime("%H:%M:%S") if a.check_in else "",
        "Checkout"       : a.checkout.strftime("%H:%M:%S") if a.checkout else "",
        "Status"          : a.status,
        "total_work_duration"   : a.total_work_duration,       # adjust if timedelta
        "total_break_duration"  : a.total_break_duration,
    } for a in qs.order_by("date", "user__username")]

    df = pd.DataFrame(records)

    # 5️⃣  Stream the CSV back
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="attendance_{date.today()}.csv"'
    df.to_csv(response, index=False)
    return response


@staff_member_required
def device_logs(request):
    logs = DeviceLog.objects.select_related("user").order_by("-last_seen")
    return render(request, "accounts/device_logs.html", {"logs": logs})
