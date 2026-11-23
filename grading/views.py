from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, redirect, render
from quizzes.models import Quiz
from questions.models import Choice
from .models import Attempt, SubmittedAnswer
from .services import grade_objective_answers


@login_required
def take_quiz(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, is_published=True, course__is_approved=True)
    if request.user.role != 'STUDENT':
        raise PermissionDenied
    if Attempt.objects.filter(quiz=quiz, student=request.user).exists():
        return redirect('grading:results')
    questions = quiz.quizquestion_set.select_related('question').prefetch_related('question__choices')
    if request.method == 'POST':
        attempt = Attempt.objects.create(quiz=quiz, student=request.user)
        for assignment in questions:
            question = assignment.question
            choice_id = request.POST.get(f'question_{question.id}')
            selected_ids = request.POST.getlist(f'question_{question.id}')
            written = request.POST.get(f'written_{question.id}', '').strip()
            choice = None
            if question.kind in ('MCQ', 'TRUE_FALSE') and choice_id:
                choice = get_object_or_404(Choice, pk=choice_id, question=question)
            if question.kind == 'MULTI_SELECT':
                valid_choices = list(Choice.objects.filter(question=question, pk__in=selected_ids))
                written = ','.join(str(item.pk) for item in valid_choices)
            if question.kind == 'BLANKS':
                written = request.POST.get(f'blank_{question.id}', '').strip()
                choice = question.choices.first()
            SubmittedAnswer.objects.create(attempt=attempt, question=question, selected_choice=choice, written_answer=written)
        grade_objective_answers(attempt)
        messages.success(request, 'Your quiz was submitted successfully.')
        return redirect('grading:results')
    return render(request, 'grading/take_quiz.html', {'quiz': quiz, 'assignments': questions})


@login_required
def results(request):
    attempts = Attempt.objects.filter(student=request.user).select_related('quiz', 'quiz__course').order_by('-started_at') if request.user.role == 'STUDENT' else Attempt.objects.none()
    released_attempts = attempts.filter(is_released=True)
    grade_summary = released_attempts.aggregate(
        total_marks=Sum('score'),
        average_marks=Avg('score'),
    )
    return render(request, 'shared/list.html', {
        'title': 'My submissions',
        'items': attempts,
        'total_marks': grade_summary['total_marks'] or 0,
        'average_marks': grade_summary['average_marks'],
    })


@login_required
def grade_attempt(request, pk):
    if request.user.role == 'ADMIN' or request.user.is_superuser:
        messages.info(request, 'Submission review is available to faculty only.')
        return redirect('users:home')
    if request.user.role != 'FACULTY':
        raise PermissionDenied
    attempt = get_object_or_404(Attempt.objects.select_related('quiz__course'), pk=pk)
    answers = attempt.answers.select_related('question', 'selected_choice')
    if request.method == 'POST':
        for answer in answers:
            value = request.POST.get(f'points_{answer.id}', '0')
            try:
                answer.awarded_points = max(0, min(int(value), answer.question.points))
            except ValueError:
                answer.awarded_points = 0
            answer.save(update_fields=['awarded_points'])
        attempt.score = sum(attempt.answers.values_list('awarded_points', flat=True))
        attempt.is_graded = True
        attempt.is_released = request.POST.get('release') == 'yes'
        attempt.save(update_fields=['score', 'is_graded', 'is_released'])
        if attempt.is_released:
            messages.success(request, 'Grade saved and released to the student.')
        else:
            messages.success(request, 'Grade saved. The result is not visible to the student yet.')
        return redirect('grading:attempts')
    return render(request, 'grading/grade_attempt.html', {'attempt': attempt, 'answers': answers})


@login_required
def attempt_list(request):
    if request.user.role == 'ADMIN' or request.user.is_superuser:
        messages.info(request, 'Submission review is available to faculty only.')
        return redirect('users:home')
    if request.user.role != 'FACULTY':
        raise PermissionDenied
    attempts = Attempt.objects.select_related('student', 'quiz', 'quiz__course').all()
    return render(request, 'shared/list.html', {'title': 'Attempts to grade', 'items': attempts, 'grade_attempts': True})
