from django.conf import settings
from django.db import models


class Course(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    admin_suggestion = models.TextField(blank=True)
    faculty = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='courses_taught')
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
                                      related_name='courses_enrolled')

    def __str__(self):
        return self.name
