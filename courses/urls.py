from django.urls import path
from . import views

app_name = 'courses'
urlpatterns = [
    path('', views.course_list, name='list'),
    path('create/', views.course_create, name='create'),
    path('<int:pk>/edit/', views.course_edit, name='edit'),
    path('<int:pk>/delete/', views.course_delete, name='delete'),
    path('<int:pk>/review/', views.course_review, name='review'),
    path('<int:pk>/', views.course_detail, name='detail'),
]
