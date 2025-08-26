from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("superadmin/", views.superadmin_dashboard, name="superadmin_dashboard"),
    path("superadmin/departments/", views.manage_departments, name="manage_departments"),
    path("superadmin/departments/<int:pk>/", views.department_detail, name="department_detail"),
    path("superadmin/manage/", views.manage_issues, name="manage_issues"),
    path("superadmin/assign-department/<int:issue_id>/", views.assign_department, name="assign_department"),
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.citizen_dashboard, name='citizen_dashboard'),
    path('report-issue/', views.report_issue, name='report_issue'),
    path('issues/', views.view_all_issues, name='view_all_issues'),
    path("issues/<int:pk>/", views.issue_detail, name="issue_detail"),
    path("issues/<int:pk>/comment/", views.add_comment, name="add_comment"),
    path("issues/<int:pk>/comment/<int:parent_id>/", views.add_comment, name="add_comment"),
    path('vote/<int:issue_id>/', views.vote_issue, name='vote_issue'),  
    path("department/", views.department_dashboard, name="department_dashboard"), 
    path("update-issue-status/<int:issue_id>/", views.update_issue_status, name="update_issue_status"),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('ban-user/<int:user_id>/', views.ban_user, name='ban_user'),
    path('unban-user/<int:user_id>/', views.unban_user, name='unban_user'),
    path('issues/<int:issue_id>/delete_fake/', views.delete_fake_issue, name='delete_fake_issue'),
    path("reports/", views.superadmin_reports, name="superadmin_reports"),
]