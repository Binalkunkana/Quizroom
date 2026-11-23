from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from grading.models import Attempt
from .models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ('name', 'description', 'students')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CS101: Introduction to Computer Science'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Overview and topics covered in this course...'}),
            'students': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show enrolled candidates who are students
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['students'].queryset = User.objects.filter(role='STUDENT').order_by('username')
        self.fields['students'].help_text = 'Check students who are enrolled in this course.'


@login_required
def course_list(request):
    if request.user.is_superuser or request.user.role == 'ADMIN':
        courses = Course.objects.all()
    elif request.user.role == 'FACULTY':
        courses = Course.objects.filter(faculty=request.user)
    elif request.user.role == 'STUDENT':
        courses = Course.objects.filter(is_approved=True)
    else:
        courses = Course.objects.none()
    courses = courses.select_related('faculty').annotate(
        enrolled_student_count=Count('students', distinct=True)
    )
    return render(request, 'shared/list.html', {
        'title': 'Courses',
        'items': courses,
        'create_url': 'courses:create' if request.user.role == 'FACULTY' else None,
    })


@login_required
def course_create(request):
    if request.user.role != 'FACULTY':
        raise PermissionDenied
    form = CourseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        course = form.save(commit=False)
        course.faculty = request.user
        course.is_approved = False
        course.save()
        form.save_m2m()
        messages.success(request, 'Course submitted for admin approval.')
        return redirect('courses:list')
    return render(request, 'shared/form.html', {'title': 'Create course', 'form': form})


@login_required
def course_edit(request, pk):
    if request.user.role != 'FACULTY':
        raise PermissionDenied
    course = get_object_or_404(Course, pk=pk, faculty=request.user)
    form = CourseForm(request.POST or None, instance=course)
    if request.method == 'POST' and form.is_valid():
        course = form.save(commit=False)
        course.is_approved = False
        course.admin_suggestion = ''
        course.save()
        form.save_m2m()
        messages.success(request, 'Course changes submitted for admin approval.')
        return redirect('courses:detail', pk=course.pk)
    return render(request, 'shared/form.html', {
        'title': 'Edit course',
        'form': form,
    })


@login_required
def course_delete(request, pk):
    if request.user.role != 'FACULTY':
        raise PermissionDenied
    course = get_object_or_404(Course, pk=pk, faculty=request.user)
    if request.method == 'POST':
        course_name = course.name
        course.delete()
        messages.success(request, f'{course_name} and its related content were deleted.')
        return redirect('courses:list')
    return render(request, 'shared/confirm_delete.html', {
        'title': 'Delete course',
        'object': course,
        'related_content_warning': (
            'Deleting this course also permanently deletes its quizzes, '
            'questions, student enrollments, and quiz attempts.'
        ),
    })


@login_required
def course_review(request, pk):
    if request.method != 'POST' or not (
        request.user.is_superuser or request.user.role == 'ADMIN'
    ):
        raise PermissionDenied

    course = get_object_or_404(Course, pk=pk)
    action = request.POST.get('action')
    if action == 'approve':
        course.is_approved = True
        course.save(update_fields=['is_approved'])
        messages.success(request, f'{course.name} has been approved.')
    elif action == 'suggest':
        suggestion = request.POST.get('admin_suggestion', '').strip()
        if not suggestion:
            messages.error(request, 'Enter a correction suggestion before sending it.')
        else:
            course.admin_suggestion = suggestion
            course.save(update_fields=['admin_suggestion'])
            messages.success(request, 'Your correction suggestion was sent to the faculty member.')
    else:
        raise PermissionDenied
    return redirect('courses:detail', pk=course.pk)


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.user.role == 'STUDENT' and not course.is_approved:
        raise PermissionDenied
    if request.user.role == 'FACULTY' and course.faculty_id != request.user.id:
        raise PermissionDenied
    if not (request.user.is_superuser or request.user.role in ('ADMIN', 'FACULTY', 'STUDENT')):
        raise PermissionDenied
    attempted_quiz_ids = set()
    if request.user.role == 'STUDENT':
        attempts = Attempt.objects.filter(student=request.user, quiz__course=course)
        attempted_quiz_ids = set(attempts.values_list('quiz_id', flat=True))
    return render(request, 'courses/detail.html', {
        'course': course,
        'enrolled_student_count': course.students.filter(role='STUDENT').distinct().count(),
        'attempted_quiz_ids': attempted_quiz_ids,
    })
