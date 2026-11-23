from django.contrib import admin
from .models import Attempt, SubmittedAnswer

class SubmittedAnswerInline(admin.TabularInline):
    model = SubmittedAnswer
    extra = 0

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'score', 'is_graded', 'is_released')
    inlines = (SubmittedAnswerInline,)

admin.site.register(SubmittedAnswer)
