from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from courses.models import Course
from .models import Choice, Question


class QuestionForm(forms.ModelForm):
    option_1 = forms.CharField(required=False, label='Option 1', widget=forms.TextInput(attrs={'class': 'form-control'}))
    option_2 = forms.CharField(required=False, label='Option 2', widget=forms.TextInput(attrs={'class': 'form-control'}))
    option_3 = forms.CharField(required=False, label='Option 3', widget=forms.TextInput(attrs={'class': 'form-control'}))
    option_4 = forms.CharField(required=False, label='Option 4', widget=forms.TextInput(attrs={'class': 'form-control'}))
    correct_options = forms.MultipleChoiceField(required=False, label='Correct answer(s)', choices=(), widget=forms.CheckboxSelectMultiple)
    blank_answer = forms.CharField(required=False, label='Correct answer', widget=forms.TextInput(attrs={'class': 'form-control'}))
    correct_tf = forms.ChoiceField(required=False, label='Correct answer', choices=(('True', 'True'), ('False', 'False')), widget=forms.RadioSelect)
    class Meta:
        model = Question
        fields = ('course', 'text', 'kind', 'points')
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Type your question prompt here...'}),
            'kind': forms.Select(attrs={'class': 'form-select', 'id': 'id_kind'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': '1'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not (user.is_superuser or user.role == 'ADMIN'):
            self.fields['course'].queryset = Course.objects.filter(faculty=user)
        values = self.data if self.is_bound else {}
        self.fields['correct_options'].choices = [(str(i), values.get(f'option_{i}', f'Option {i}') or f'Option {i}') for i in range(1, 5)]
        if self.instance.pk and not self.is_bound:
            choices = list(self.instance.choices.all())
            if self.instance.kind in (Question.Kind.MCQ, Question.Kind.MULTI_SELECT):
                correct_option_indexes = []
                for i, choice in enumerate(choices[:4], 1):
                    self.fields[f'option_{i}'].initial = choice.text
                    if choice.is_correct:
                        correct_option_indexes.append(str(i))
                self.fields['correct_options'].initial = correct_option_indexes
                self.fields['correct_options'].choices = [
                    (str(i), self.fields[f'option_{i}'].initial or f'Option {i}') for i in range(1, 5)
                ]
            elif self.instance.kind == Question.Kind.TRUE_FALSE:
                self.fields['correct_tf'].initial = next((c.text for c in choices if c.is_correct), '')
            elif self.instance.kind == Question.Kind.BLANKS and choices:
                self.fields['blank_answer'].initial = choices[0].text

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get('kind')
        if kind in (Question.Kind.MCQ, Question.Kind.MULTI_SELECT):
            options = [cleaned.get(f'option_{i}', '').strip() for i in range(1, 5)]
            selected = cleaned.get('correct_options', [])
            if not any(options):
                self.add_error('option_1', 'Enter at least two options.')
            elif sum(bool(option) for option in options) < 2:
                self.add_error('option_2', 'Enter at least two options.')
            if not selected:
                self.add_error('correct_options', 'Select at least one correct answer.')
            if kind == Question.Kind.MCQ and len(selected) > 1:
                self.add_error('correct_options', 'Choose only one correct answer for multiple choice.')
            if any(not options[int(index) - 1] for index in selected):
                self.add_error('correct_options', 'A correct answer must have option text.')
        elif kind == Question.Kind.BLANKS and not cleaned.get('blank_answer', '').strip():
            self.add_error('blank_answer', 'Enter the expected answer.')
        elif kind == Question.Kind.TRUE_FALSE and not cleaned.get('correct_tf'):
            self.add_error('correct_tf', 'Choose True or False.')
        return cleaned


@login_required
def question_list(request):
    if request.user.role == 'FACULTY':
        qs = Question.objects.select_related('course')
    else:
        raise PermissionDenied
    return render(request, 'shared/list.html', {
        'title': 'Questions',
        'items': qs,
        'create_url': 'questions:create',
    })


@login_required
def question_create(request):
    if request.user.role != 'FACULTY':
        raise PermissionDenied
    form = QuestionForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        question = form.save(commit=False)
        if question.course.faculty_id != request.user.id:
            raise PermissionDenied
        question.created_by = request.user
        question.save()
        if question.kind in (Question.Kind.MCQ, Question.Kind.MULTI_SELECT):
            correct = set(form.cleaned_data['correct_options'])
            for i in range(1, 5):
                text = form.cleaned_data.get(f'option_{i}', '').strip()
                if text:
                    Choice.objects.create(question=question, text=text, is_correct=str(i) in correct)
        elif question.kind == Question.Kind.TRUE_FALSE:
            correct = form.cleaned_data.get('correct_tf')
            for value in ('True', 'False'):
                Choice.objects.create(question=question, text=value, is_correct=value == correct)
        elif question.kind == Question.Kind.BLANKS:
            Choice.objects.create(question=question, text=form.cleaned_data['blank_answer'].strip(), is_correct=True)
        return redirect('questions:list')
    return render(request, 'shared/form.html', {'title': 'Create question', 'form': form})


def _question_for_editor(request, pk):
    question = get_object_or_404(Question.objects.select_related('course'), pk=pk)
    if request.user.role != 'FACULTY' or question.course.faculty_id != request.user.id:
        raise PermissionDenied
    return question


@login_required
def question_edit(request, pk):
    question = _question_for_editor(request, pk)
    form = QuestionForm(request.POST or None, instance=question, user=request.user)
    if request.method == 'POST' and form.is_valid():
        question = form.save()
        question.choices.all().delete()
        if question.kind in (Question.Kind.MCQ, Question.Kind.MULTI_SELECT):
            correct = set(form.cleaned_data['correct_options'])
            for i in range(1, 5):
                text = form.cleaned_data.get(f'option_{i}', '').strip()
                if text:
                    Choice.objects.create(question=question, text=text, is_correct=str(i) in correct)
        elif question.kind == Question.Kind.TRUE_FALSE:
            for value in ('True', 'False'):
                Choice.objects.create(question=question, text=value, is_correct=value == form.cleaned_data['correct_tf'])
        elif question.kind == Question.Kind.BLANKS:
            Choice.objects.create(question=question, text=form.cleaned_data['blank_answer'].strip(), is_correct=True)
        return redirect('questions:list')
    return render(request, 'shared/form.html', {'title': 'Edit question', 'form': form})


@login_required
def question_delete(request, pk):
    question = _question_for_editor(request, pk)
    if request.method == 'POST':
        question.delete()
        return redirect('questions:list')
    return render(request, 'shared/confirm_delete.html', {'title': 'Delete question', 'object': question})
