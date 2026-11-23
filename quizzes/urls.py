from django.urls import path
from . import views

app_name = 'quizzes'
urlpatterns = [path('', views.quiz_list, name='list'),
                path('create/', views.quiz_create, name='create'), 
                path('<int:pk>/publish/', views.quiz_publish, name='publish'),
                path('<int:pk>/edit/', views.quiz_edit, name='edit'), 
                path('<int:pk>/delete/', views.quiz_delete, name='delete')]
