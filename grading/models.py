from django.conf import settings
from django.db import models


class Attempt(models.Model):
    quiz = models.ForeignKey('quizzes.Quiz', on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    score = models.PositiveIntegerField(default=0)
    is_graded = models.BooleanField(default=False)
    is_released = models.BooleanField(default=False)

    class Meta:
        unique_together = ('quiz', 'student')

    def __str__(self):
        return f'{self.student} - {self.quiz}'

    @property
    def current_score(self):
        return sum(self.answers.values_list('awarded_points', flat=True))


class SubmittedAnswer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey('questions.Question', on_delete=models.CASCADE)
    selected_choice = models.ForeignKey('questions.Choice', null=True, blank=True, on_delete=models.SET_NULL)
    written_answer = models.TextField(blank=True)
    awarded_points = models.PositiveIntegerField(default=0)
