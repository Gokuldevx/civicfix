from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    is_citizen = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    is_resolver = models.BooleanField(default=False)
    phone = models.CharField(max_length=15, blank=True, null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='core_user_groups',
        related_query_name='core_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='core_user_permissions',
        related_query_name='core_user',
    )

    # Ban-related fields
    is_banned = models.BooleanField(default=False)
    banned_until = models.DateTimeField(null=True, blank=True)

    def ban(self, days=7):
        """Ban user for given number of days (default = 7)."""
        self.is_banned = True
        self.banned_until = timezone.now() + timedelta(days=days)
        self.save()

    def unban(self):
        """Unban user immediately."""
        self.is_banned = False
        self.banned_until = None
        self.save()

    def is_currently_banned(self):
        """Check if user is still banned (auto-unban if expired)."""
        if self.is_banned and self.banned_until:
            if timezone.now() >= self.banned_until:
                # Auto unban if ban expired
                self.unban()
                return False
            return True
        return False
    
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Each department can have many users
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="departments",
        blank=True
    )

    # One admin per department
    admin = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="admin_of_department",
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class Issue(models.Model):
    STATUS_REPORTED = 'reported'
    STATUS_ACKNOWLEDGED = 'acknowledged'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_RESOLVED = 'resolved'

    STATUS_CHOICES = [
        (STATUS_REPORTED, 'Reported'),
        (STATUS_ACKNOWLEDGED, 'Acknowledged'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_RESOLVED, 'Resolved'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reported_issues"
    )

    # 🔹 Add relation to department
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issues"
    )

    location = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    photo = models.ImageField(
        upload_to="issue_photos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])]
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_REPORTED
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  # 🔹 latest issues first by default

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    # 🔹 Helpers
    def vote_count(self):
        return self.votes.count() if hasattr(self, "votes") else 0

    def has_user_voted(self, user):
        if user.is_authenticated and hasattr(self, "votes"):
            return self.votes.filter(user=user).exists()
        return 
    
    def assign_to_department(self, department):
        """Assign issue to a department and auto-update status to acknowledged"""
        self.department = department
        self.status = self.STATUS_ACKNOWLEDGED
        self.save()
    

    
class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='votes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'issue')  # Prevent duplicate votes per user

    def __str__(self):
        return f"{self.user.username} voted on {self.issue.title}"

class Comment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()   # <--- field name is "content", not "text"
    parent = models.ForeignKey("self", null=True, blank=True, related_name="replies", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user} on {self.issue}"

    @property
    def is_reply(self):
        return self.parent is not None