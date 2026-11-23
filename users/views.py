from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from courses.models import Course
from quizzes.models import Quiz
from grading.models import Attempt

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('username', 'password1', 'password2'):
            self.fields[field_name].help_text = ''
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm password'
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})

    def validate_password_for_user(self, user, password_field_name='password2'):
        # Keep both password fields required and matching, but don't apply
        # Django's strength/similarity validators on this simple admin form.
        return


class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }


def _admin_managed_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.is_superuser or user.pk == request.user.pk:
        raise PermissionDenied
    return user


@login_required
def home(request):
    context = {}
    if request.user.role == 'STUDENT':
        context['course_count'] = Course.objects.count()
        context['quiz_count'] = Quiz.objects.filter(is_published=True).count()
        context['pending_count'] = Attempt.objects.filter(student=request.user, is_released=False).count()
        context['recent_quizzes'] = Quiz.objects.filter(is_published=True).select_related('course')[:5]
        context['recent_attempts'] = Attempt.objects.filter(student=request.user).select_related('quiz').order_by('-started_at')[:5]
    elif request.user.role == 'FACULTY':
        context['course_count'] = Course.objects.filter(faculty=request.user).count()
        context['quiz_count'] = Quiz.objects.count()
        context['pending_count'] = Attempt.objects.filter(is_released=False).count()
        context['recent_attempts'] = Attempt.objects.filter(is_released=False).select_related('student', 'quiz')[:5]
        context['recent_quizzes'] = Quiz.objects.all().select_related('course')[:5]
        context['owned_courses'] = Course.objects.filter(faculty=request.user).annotate(
            enrolled_student_count=Count('students', distinct=True),
        ).order_by('name')[:5]
    elif request.user.role == 'ADMIN' or request.user.is_superuser:
        context['user_count'] = User.objects.count()
        context['course_count'] = Course.objects.count()
        context['faculty'] = User.objects.filter(role='FACULTY').annotate(
            course_count=Count('courses_taught', distinct=True),
        ).order_by('first_name', 'last_name', 'username')
        context['faculty_count'] = context['faculty'].count()
        context['recent_users'] = User.objects.order_by('-date_joined')[:5]
    return render(request, 'users/home.html', context)


@login_required
@user_passes_test(lambda user: user.is_superuser or user.role == 'ADMIN')
def user_list(request):
    return render(request, 'shared/list.html', {'title': 'Users', 'items': User.objects.all(), 'create_url': 'users:create'})


@login_required
@user_passes_test(lambda user: user.is_superuser or user.role == 'ADMIN')
def user_create(request):
    form = CustomUserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        user.role = request.POST.get('role', 'STUDENT')
        if user.role not in User.Role.values:
            user.role = 'STUDENT'
        user.save()
        messages.success(request, 'User created successfully.')
        return redirect('users:list')
    return render(request, 'shared/form.html', {'title': 'Create user', 'form': form, 'extra_role_field': True})


@login_required
@user_passes_test(lambda user: user.is_superuser or user.role == 'ADMIN')
def user_edit(request, pk):
    managed_user = _admin_managed_user(request, pk)
    form = UserDetailsForm(request.POST or None, instance=managed_user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'User details updated successfully.')
        return redirect('users:list')
    return render(request, 'shared/form.html', {'title': 'Edit user', 'form': form})


@login_required
@user_passes_test(lambda user: user.is_superuser or user.role == 'ADMIN')
def user_delete(request, pk):
    managed_user = _admin_managed_user(request, pk)
    if request.method == 'POST':
        managed_user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('users:list')
    return render(request, 'shared/confirm_delete.html', {'title': 'Delete user', 'object': managed_user})
