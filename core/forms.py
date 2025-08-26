from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Issue, Comment

class CitizenRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.is_citizen = True
        
        if commit:
            user.save()
        return user

class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['title', 'description', 'location', 'latitude', 'longitude', 'photo']
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the issue in detail...'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 2, "placeholder": "Add a comment..."})
        }

class IssueAssignForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['department']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }