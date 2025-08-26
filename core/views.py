from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.db import IntegrityError
from django.db.models import Exists, OuterRef, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.timezone import now, timedelta
from django.views.decorators.http import require_POST
from .models import Issue, User, Vote, Comment, Department
from .forms import CitizenRegistrationForm, IssueForm, CommentForm

def home(request):
    total_issues = Issue.objects.count()
    resolved_issues = Issue.objects.filter(status=Issue.STATUS_RESOLVED).count()
    active_users = User.objects.filter(is_active=True).count()
    total_departments = Department.objects.count()
    
    recent_issues = Issue.objects.all().order_by('-created_at')[:3]
    
    for issue in recent_issues:
        issue.user_has_voted = issue.has_user_voted(request.user) if request.user.is_authenticated else False

    
    context = {
        'total_issues': total_issues,
        'resolved_issues': resolved_issues,
        'active_users': active_users,
        'total_departments': total_departments,
        'recent_issues': recent_issues,
    }
    return render(request, 'core/index.html', context)


@login_required
def citizen_dashboard(request):
    if not request.user.is_citizen:
        messages.error(request, 'Access denied. Citizen role required.')
        return redirect('home')
    
    # Get only basic data for now
    all_user_issues = Issue.objects.filter(reporter=request.user)
    user_issues_display = all_user_issues.order_by('-created_at')[:5]
    resolved_count = all_user_issues.filter(status='resolved').count()
    
    context = {
        'user_issues': user_issues_display, 
        'resolved_count': resolved_count,    
        'issue_form': IssueForm(),
    }
    return render(request, 'dashboard/citizen_dashboard.html', context)

@login_required
def report_issue(request):
    if not request.user.is_citizen:
        messages.error(request, 'Access denied. Citizen role required.')
        return redirect('home')
    
    if request.method == 'POST':
        form = IssueForm(request.POST, request.FILES)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.reporter = request.user
            issue.status = "reported"  # default status
            issue.save()
            messages.success(request, 'Issue reported successfully!')
            return redirect('citizen_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = IssueForm()
    
    return render(request, 'core/report_issue.html', {'form': form})

@login_required
def view_all_issues(request):
    if not request.user.is_citizen:
        messages.error(request, 'Access denied. Citizen role required.')
        return redirect('home')

    # Efficiently annotate whether the current user has voted
    user_vote_subq = Vote.objects.filter(user=request.user, issue_id=OuterRef('pk'))
    issues = (
        Issue.objects
        .select_related('reporter')
        .annotate(user_has_voted=Exists(user_vote_subq))
        .order_by('-created_at')
    )

    # Optional filter (status only now)
    status = request.GET.get('status') or ''
    if status:
        issues = issues.filter(status=status)

    return render(request, 'issues/view_all_issues.html', {
        'issues': issues,
        'selected_status': status,
    })


def register(request):
    if request.method == 'POST':
        form = CitizenRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
    else:
        form = CitizenRegistrationForm()
    
    return render(request, 'core/register.html', {'form': form})

def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                # 🔹 Auto unban check
                if hasattr(user, "is_currently_banned") and user.is_currently_banned():
                    days_left = (user.banned_until - timezone.now()).days
                    messages.error(
                        request,
                        f"🚫 Your account is banned for {days_left} more days for reporting a fake issue."
                    )
                    return redirect('login')

                # Normal login
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'core/login.html', {'form': form})

@login_required
@require_POST
def vote_issue(request, issue_id):
    try:
        issue = Issue.objects.get(id=issue_id)
        vote, created = Vote.objects.get_or_create(user=request.user, issue=issue)
        
        if not created:
            # User already voted, so remove the vote (toggle)
            vote.delete()
            voted = False
        else:
            voted = True
        
        return JsonResponse({
            'success': True,
            'voted': voted,
            'vote_count': issue.vote_count()
        })
        
    except Issue.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Issue not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
@login_required
def add_comment(request, pk, parent_id=None):
    issue = get_object_or_404(Issue, pk=pk)
    parent = get_object_or_404(Comment, pk=parent_id) if parent_id else None

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.issue = issue
            comment.user = request.user
            comment.parent = parent
            comment.save()
    return redirect("issue_detail", pk=pk)

def issue_detail(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    comments = issue.comments.filter(parent__isnull=True)  # top-level comments
    return render(request, "issues/issue_detail.html", {"issue": issue, "comments": comments})

def add_comment(request, pk, parent_id=None):
    if request.method == "POST" and request.user.is_authenticated:
        issue = get_object_or_404(Issue, pk=pk)
        text = request.POST.get("text")
        content = request.POST.get("content")
    if content:
        parent = Comment.objects.get(pk=parent_id) if parent_id else None
        Comment.objects.create(issue=issue, user=request.user, content=content, parent=parent)
    return redirect("issue_detail", pk=pk)

def superadmin_check(user):
    return user.is_superuser  

@login_required
@user_passes_test(superadmin_check)
def superadmin_dashboard(request):
    return render(request, "dashboard/superadmin_dashboard.html")

@login_required
@user_passes_test(superadmin_check)
def manage_departments(request):
    departments = Department.objects.all().order_by("name")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        if name:
            Department.objects.create(name=name, description=description)
            return redirect("manage_departments")

    return render(request, "department/manage_departments.html", {
        "departments": departments
    })

@login_required
@user_passes_test(superadmin_check)
def department_detail(request, pk):
    department = get_object_or_404(Department, pk=pk)
    users = department.users.all()

    if request.method == "POST":
        # ---- Create user ----
        if "create_user" in request.POST:
            username = request.POST.get("username", "").strip()
            email = request.POST.get("email", "").strip()
            password = request.POST.get("password", "").strip()
            if username and password:
                try:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password
                    )
                    user.is_resolver = True
                    user.save()
                    department.users.add(user)
                    messages.success(request, f"User '{username}' created and added to department.")
                except IntegrityError:
                    messages.error(request, "Username already exists.")

        # ---- Assign admin ----
        elif "assign_admin" in request.POST:
            user_id = request.POST.get("admin_user_id")
            if user_id:
                user = get_object_or_404(User, id=user_id)
                department.admin = user
                department.save()
                messages.success(request, f"{user.username} is now the admin of {department.name}.")

        # ---- Remove admin ----
        elif "remove_admin" in request.POST:
            department.admin = None
            department.save()
            messages.info(request, "Department admin removed.")

        return redirect("department_detail", pk=department.id)

    return render(request, "department/department_detail.html", {
        "department": department,
        "users": users,
    })

@login_required
@user_passes_test(superadmin_check)
def manage_issues(request):
    issues = Issue.objects.all().order_by('-created_at')

    if request.method == "POST":
        issue_id = request.POST.get("issue_id")
        dept_id = request.POST.get("department")

        issue = get_object_or_404(Issue, id=issue_id)
        if dept_id:  # Only assign if a department is selected
            department = get_object_or_404(Department, id=dept_id)
            issue.assign_to_department(department)  # 🔹 uses helper
        return redirect("manage_issues")  # refresh page after save

    return render(request, "issues/manage_issues.html", {
    "issues": issues,
    "departments": Department.objects.all()
})

@user_passes_test(superadmin_check)
def assign_department(request, issue_id):
    if request.method == "POST":
        issue = get_object_or_404(Issue, id=issue_id)
        dept_id = request.POST.get("department_id")

        if dept_id:
            department = get_object_or_404(Department, id=dept_id)
            issue.assign_to_department(department)
            messages.success(request, f"Issue '{issue.title}' assigned to {department.name}.")
        else:
            messages.error(request, "Please select a department.")

    return redirect("manage_issues") 

@login_required
@user_passes_test(superadmin_check)
def manage_users(request):
    citizens = User.objects.filter(is_citizen=True).order_by('-date_joined')
    return render(request, 'core/manage_users.html', {'citizens': citizens})


@login_required
@user_passes_test(superadmin_check)
def ban_user(request, user_id):
    citizen = get_object_or_404(User, id=user_id, is_citizen=True)
    citizen.ban(days=7)  # default ban 7 days
    messages.warning(request, f"{citizen.username} has been banned for 7 days.")
    return redirect('manage_users')

@login_required
@user_passes_test(superadmin_check)
def unban_user(request, user_id):
    citizen = get_object_or_404(User, id=user_id, is_citizen=True)
    citizen.unban()
    messages.success(request, f"{citizen.username} has been unbanned.")
    return redirect('manage_users')

@login_required
@user_passes_test(superadmin_check)
def delete_fake_issue(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    reporter = issue.reporter 
    reporter.ban(7)
    issue.delete()
    messages.success(request, f"✅ Issue deleted and user {reporter.username} has been banned for 7 days.")
    return redirect("manage_issues")

@login_required
@user_passes_test(superadmin_check)
def superadmin_reports(request):
    # 1. Total issues reported
    total_issues = Issue.objects.count()

    # 2. Issues per status
    status_counts = (
        Issue.objects.values('status')
        .annotate(count=Count('id'))
        .order_by()
    )

    # 3. Top 5 departments with most assigned issues
    top_departments = (
        Issue.objects.values('department__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # 4. Top citizens by number of reports
    top_citizens = (
        Issue.objects.values('reporter__username')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # 5. Issues over time (last 30 days)
    last_30_days = now() - timedelta(days=30)
    issues_last_30_days = (
        Issue.objects.filter(created_at__gte=last_30_days)
        .extra(select={'day': "date(created_at)"})
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    context = {
        "total_issues": total_issues,
        "status_counts": list(status_counts),
        "top_departments": list(top_departments),
        "top_citizens": list(top_citizens),
        "issues_last_30_days": list(issues_last_30_days),
    }
    return render(request, "core/superadmin_reports.html", context)

def resolver_check(user):
    return user.is_resolver

@login_required
@user_passes_test(lambda u: u.is_resolver)
def department_dashboard(request):
    departments = request.user.departments.all()
    issues = Issue.objects.filter(department__in=departments).order_by('-created_at')
    return render(request, "dashboard/department_dashboard.html", {"issues": issues, "departments": departments})

@login_required
@user_passes_test(lambda u: u.is_resolver)
def update_issue_status(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)

    # Make sure the user belongs to the department assigned to the issue
    if issue.department not in request.user.departments.all():
        return redirect("department_dashboard")

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in [Issue.STATUS_IN_PROGRESS, Issue.STATUS_RESOLVED]:
            issue.status = new_status
            issue.save()
    return redirect("department_dashboard")
