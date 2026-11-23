from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from quizzes.models import Quiz
from .models import Attempt


User = get_user_model()


class AttemptListPermissionTests(TestCase):
    def test_admin_cannot_access_submissions_but_faculty_can(self):
        admin = User.objects.create_user(
            username='admin', password='password', role='ADMIN',
        )
        faculty = User.objects.create_user(
            username='faculty', password='password', role='FACULTY',
        )
        url = reverse('grading:attempts')

        self.client.force_login(admin)
        response = self.client.get(url)
        self.assertRedirects(response, reverse('users:home'))
        self.assertEqual(
            list(response.wsgi_request._messages)[0].message,
            'Submission review is available to faculty only.',
        )

        self.client.force_login(faculty)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_student_submission_summary_calculates_released_attempts(self):
        student = User.objects.create_user(
            username='student', password='password', role='STUDENT',
        )
        faculty = User.objects.create_user(
            username='faculty', password='password', role='FACULTY',
        )
        course = Course.objects.create(name='Mathematics', faculty=faculty)
        quiz_one = Quiz.objects.create(title='Quiz 1', course=course)
        quiz_two = Quiz.objects.create(title='Quiz 2', course=course)
        quiz_three = Quiz.objects.create(title='Quiz 3', course=course)
        Attempt.objects.create(
            quiz=quiz_one, student=student, score=80,
            is_graded=True, is_released=True,
        )
        Attempt.objects.create(
            quiz=quiz_two, student=student, score=60,
            is_graded=True, is_released=True,
        )
        Attempt.objects.create(
            quiz=quiz_three, student=student, score=100,
            is_graded=False, is_released=False,
        )
        self.client.force_login(student)

        response = self.client.get(reverse('grading:results'))

        self.assertContains(response, 'Total marks')
        self.assertContains(response, 'Average marks')
        self.assertEqual(response.context['total_marks'], 140)
        self.assertEqual(response.context['average_marks'], 70)
