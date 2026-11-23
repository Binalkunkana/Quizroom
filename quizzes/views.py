from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from courses.models import Course
from questions.models import Question
from grading.models import Attempt
from .models import Quiz, QuizQuestion


class QuizForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        label='Course',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    title = forms.CharField(
        max_length=150,
        label='Quiz title',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Midterm Examination'})
    )
    time_limit_minutes = forms.IntegerField(
        min_value=1,
        initial=30,
        label='Time limit (minutes)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': '30'})
    )
    questions = forms.ModelMultipleChoiceField(
        queryset=Question.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Questions to include',
        help_text='Select existing questions for the course selected above. Create questions first if this list is empty.',
    )

    def __init__(self, *args, user=None, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        courses = Course.objects.all() if user and (user.is_superuser or user.role == 'ADMIN') else Course.objects.filter(faculty=user)
        self.fields['course'].queryset = courses
        self.fields['questions'].queryset = Question.objects.filter(course__in=courses)
        if instance and not self.is_bound:
            self.fields['course'].initial = instance.course_id
            self.fields['title'].initial = instance.title
            self.fields['time_limit_minutes'].initial = instance.time_limit_minutes
            self.fields['questions'].initial = list(instance.questions.values_list('pk', flat=True))

    def clean(self):
        cleaned = super().clean()
        questions = cleaned.get('questions')
        course = cleaned.get('course')
        if not questions:
            self.add_error('questions', 'Select at least one question. If the list is empty, create a question first.')
        elif course and questions.exclude(course=course).exists():
            self.add_error('questions', 'All selected questions must belong to the course selected above.')
        return cleaned


@login_required
def quiz_list(request):
    if request.user.role == 'ADMIN' or request.user.is_superuser:
        raise PermissionDenied
    attempted_quiz_ids = set()
    if request.user.is_superuser or request.user.role == 'ADMIN':
        quizzes = Quiz.objects.all()
    elif request.user.role == 'FACULTY':
        quizzes = Quiz.objects.all()
    else:
        quizzes = Quiz.objects.filter(is_published=True, course__is_approved=True)
        attempted_quiz_ids = set(Attempt.objects.filter(student=request.user).values_list('quiz_id', flat=True))
    return render(request, 'shared/list.html', {
        'title': 'Quizzes',
        'items': quizzes,
        'attempted_quiz_ids': attempted_quiz_ids,
        'create_url': 'quizzes:create' if request.user.role in ('ADMIN', 'FACULTY') else None,
    })


@login_required
def quiz_create(request):
    if request.user.role not in ('ADMIN', 'FACULTY'):
        raise PermissionDenied
    form = QuizForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        quiz = Quiz.objects.create(course=form.cleaned_data['course'], title=form.cleaned_data['title'], time_limit_minutes=form.cleaned_data['time_limit_minutes'])
        for order, question in enumerate(form.cleaned_data['questions'], 1):
            if question.course_id != quiz.course_id:
                raise PermissionDenied
            QuizQuestion.objects.create(quiz=quiz, question=question, order=order)
        return redirect('quizzes:list')
    return render(request, 'shared/form.html', {
        'title': 'Create quiz',
        'form': form,
        'has_courses': form.fields['course'].queryset.exists(),
        'has_questions': form.fields['questions'].queryset.exists(),
    })


def _quiz_for_editor(request, pk):
    quiz = get_object_or_404(Quiz.objects.select_related('course'), pk=pk)
    if not (request.user.is_superuser or request.user.role == 'ADMIN' or
            (request.user.role == 'FACULTY' and quiz.course.faculty_id == request.user.id)):
        raise PermissionDenied
    return quiz


@login_required
def quiz_edit(request, pk):
    if request.user.role not in ('ADMIN', 'FACULTY') and not request.user.is_superuser:
        raise PermissionDenied
    quiz = _quiz_for_editor(request, pk)
    form = QuizForm(request.POST or None, user=request.user, instance=quiz)
    if request.method == 'POST' and form.is_valid():
        quiz.course = form.cleaned_data['course']
        quiz.title = form.cleaned_data['title']
        quiz.time_limit_minutes = form.cleaned_data['time_limit_minutes']
        quiz.save()
        quiz.quizquestion_set.exclude(question__in=form.cleaned_data['questions']).delete()
        existing_ids = set(quiz.quizquestion_set.values_list('question_id', flat=True))
        for order, question in enumerate(form.cleaned_data['questions'], 1):
            if question.course_id != quiz.course_id:
                raise PermissionDenied
            if question.pk in existing_ids:
                quiz.quizquestion_set.filter(question=question).update(order=order)
            else:
                QuizQuestion.objects.create(quiz=quiz, question=question, order=order)
        return redirect('quizzes:list')
    return render(request, 'shared/form.html', {
        'title': 'Edit quiz', 'form': form,
        'has_courses': form.fields['course'].queryset.exists(),
        'has_questions': form.fields['questions'].queryset.exists(),
    })


@login_required
def quiz_delete(request, pk):
    if request.user.role not in ('ADMIN', 'FACULTY') and not request.user.is_superuser:
        raise PermissionDenied
    quiz = _quiz_for_editor(request, pk)
    if request.method == 'POST':
        quiz.delete()
        return redirect('quizzes:list')
    return render(request, 'shared/confirm_delete.html', {
        'title': 'Delete quiz',
        'object': quiz,
        'related_attempt_count': quiz.attempts.count(),
    })


@login_required
def quiz_publish(request, pk):
    if request.method != 'POST' or request.user.role not in ('ADMIN', 'FACULTY'):
        raise PermissionDenied
    quiz = get_object_or_404(Quiz, pk=pk)
    if not (request.user.is_superuser or request.user.role == 'ADMIN' or quiz.course.faculty_id == request.user.id):
        raise PermissionDenied
    quiz.is_published = True
    quiz.save(update_fields=['is_published'])
    return redirect('quizzes:list')
