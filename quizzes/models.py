from django.db import models


class Quiz(models.Model):
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=150)
    questions = models.ManyToManyField('questions.Question', through='QuizQuestion')
    is_published = models.BooleanField(default=False)
    time_limit_minutes = models.PositiveIntegerField(default=30)

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.ForeignKey('questions.Question', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    class Meta:
        unique_together = ('quiz', 'question')
        ordering = ('order',)
