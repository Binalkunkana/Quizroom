from django.conf import settings
from django.db import models


class Question(models.Model):
    class Kind(models.TextChoices):
        MCQ = 'MCQ', 'Multiple choice'
        MULTI_SELECT = 'MULTI_SELECT', 'Multiple select'
        TRUE_FALSE = 'TRUE_FALSE', 'True / false'
        BLANKS = 'BLANKS', 'Fill in the blank'
        WRITTEN = 'WRITTEN', 'Written'

    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.MCQ)
    points = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.text[:80]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text
