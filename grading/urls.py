from django.urls import path
from . import views

app_name = 'grading'
urlpatterns = [path('quiz/<int:pk>/take/', views.take_quiz, name='take'), path('results/', views.results, name='results'), path('attempts/', views.attempt_list, name='attempts'), path('attempts/<int:pk>/grade/', views.grade_attempt, name='grade')]
