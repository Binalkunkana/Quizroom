from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Course
from quizzes.models import Quiz
from grading.models import Attempt


User = get_user_model()


class CourseApprovalTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', password='password', role='ADMIN',
        )
        self.faculty = User.objects.create_user(
            username='faculty', password='password', role='FACULTY',
        )
        self.student = User.objects.create_user(
            username='student', password='password', role='STUDENT',
        )

    def test_faculty_created_courses_require_admin_approval(self):
        self.client.force_login(self.faculty)

        response = self.client.post(reverse('courses:create'), {
            'name': 'Biology',
            'description': 'Introductory biology',
        })

        course = Course.objects.get(name='Biology')
        self.assertRedirects(response, reverse('courses:list'))
        self.assertEqual(course.faculty, self.faculty)
        self.assertFalse(course.is_approved)

    def test_admin_can_suggest_correction_and_approve_course(self):
        course = Course.objects.create(name='Biology', faculty=self.faculty, is_approved=False)
        self.client.force_login(self.admin)

        response = self.client.post(reverse('courses:review', args=[course.pk]), {
            'action': 'suggest',
            'admin_suggestion': 'Correct the course description.',
        })
        course.refresh_from_db()
        self.assertRedirects(response, reverse('courses:detail', args=[course.pk]))
        self.assertEqual(course.admin_suggestion, 'Correct the course description.')
        self.assertFalse(course.is_approved)

        self.client.post(reverse('courses:review', args=[course.pk]), {'action': 'approve'})
        course.refresh_from_db()
        self.assertTrue(course.is_approved)
        self.assertEqual(course.admin_suggestion, 'Correct the course description.')

    def test_faculty_can_see_admin_suggestion(self):
        course = Course.objects.create(
            name='Biology',
            faculty=self.faculty,
            admin_suggestion='Correct the course description.',
        )
        self.client.force_login(self.faculty)

        response = self.client.get(reverse('courses:detail', args=[course.pk]))

        self.assertContains(response, 'Correct the course description.')

    def test_faculty_courses_page_shows_owned_course_admin_suggestion(self):
        owned_course = Course.objects.create(
            name='Biology',
            faculty=self.faculty,
            admin_suggestion='Add a clearer course description.',
        )
        other_faculty = User.objects.create_user(
            username='other_faculty',
            password='password',
            role='FACULTY',
        )
        Course.objects.create(
            name='Chemistry',
            faculty=other_faculty,
            admin_suggestion='This suggestion must remain private.',
        )
        self.client.force_login(self.faculty)

        response = self.client.get(reverse('courses:list'))

        self.assertContains(response, 'Admin suggestion')
        self.assertContains(response, owned_course.name)
        self.assertContains(response, 'Add a clearer course description.')
        self.assertContains(response, reverse('courses:edit', args=[owned_course.pk]))
        self.assertNotContains(response, 'This suggestion must remain private.')

    def test_faculty_edit_resubmits_course_for_approval(self):
        course = Course.objects.create(
            name='Biology',
            faculty=self.faculty,
            admin_suggestion='Correct the course description.',
        )
        self.client.force_login(self.faculty)

        response = self.client.post(reverse('courses:edit', args=[course.pk]), {
            'name': 'Biology 101',
            'description': 'Updated description',
        })

        course.refresh_from_db()
        self.assertRedirects(response, reverse('courses:detail', args=[course.pk]))
        self.assertEqual(course.name, 'Biology 101')
        self.assertFalse(course.is_approved)
        self.assertEqual(course.admin_suggestion, '')

    def test_faculty_can_delete_owned_course_after_confirmation(self):
        course = Course.objects.create(name='Biology', faculty=self.faculty)
        self.client.force_login(self.faculty)

        confirmation = self.client.get(reverse('courses:delete', args=[course.pk]))
        self.assertContains(
            confirmation,
            'permanently deletes its quizzes',
        )

        response = self.client.post(reverse('courses:delete', args=[course.pk]))

        self.assertRedirects(response, reverse('courses:list'))
        self.assertFalse(Course.objects.filter(pk=course.pk).exists())

    def test_faculty_course_list_shows_edit_and_delete_actions(self):
        course = Course.objects.create(name='Biology', faculty=self.faculty)
        self.client.force_login(self.faculty)

        response = self.client.get(reverse('courses:list'))

        self.assertContains(response, reverse('courses:edit', args=[course.pk]))
        self.assertContains(response, reverse('courses:delete', args=[course.pk]))
        self.assertContains(response, 'Edit')
        self.assertContains(response, 'Delete')

    def test_admin_course_list_shows_dynamic_enrollment_count(self):
        course = Course.objects.create(name='AI/ML', faculty=self.faculty)
        course.students.add(self.student)
        self.client.force_login(self.admin)

        response = self.client.get(reverse('courses:list'))

        ai_ml_course = next(
            item for item in response.context['items']
            if item.pk == course.pk
        )
        self.assertEqual(ai_ml_course.enrolled_student_count, 1)
        self.assertContains(response, 'Enrolled students')

    def test_faculty_course_list_shows_dynamic_enrollment_count(self):
        course = Course.objects.create(name='AI/ML', faculty=self.faculty)
        course.students.add(self.student)
        self.client.force_login(self.faculty)

        response = self.client.get(reverse('courses:list'))

        ai_ml_course = next(
            item for item in response.context['items']
            if item.pk == course.pk
        )
        self.assertEqual(ai_ml_course.enrolled_student_count, 1)
        self.assertContains(response, 'Enrolled students')

    def test_faculty_cannot_delete_another_facultys_course(self):
        other_faculty = User.objects.create_user(
            username='other_faculty', password='password', role='FACULTY',
        )
        course = Course.objects.create(name='Biology', faculty=other_faculty)
        self.client.force_login(self.faculty)

        response = self.client.get(reverse('courses:delete', args=[course.pk]))

        self.assertEqual(response.status_code, 404)

    def test_course_form_offers_select_all_students(self):
        self.client.force_login(self.faculty)

        response = self.client.get(reverse('courses:create'))

        self.assertContains(response, 'id="select-all-students"')
        self.assertContains(response, 'Select all students')

    def test_students_only_see_approved_courses_and_student_enrollment_count(self):
        approved = Course.objects.create(name='Biology', faculty=self.faculty)
        approved.students.add(self.student, self.admin)
        pending = Course.objects.create(
            name='Chemistry', faculty=self.faculty, is_approved=False,
        )
        self.client.force_login(self.student)

        response = self.client.get(reverse('courses:list'))

        self.assertEqual(list(response.context['items']), [approved])
        self.assertEqual(response.context['items'][0].enrolled_student_count, 2)
        self.assertNotContains(response, 'Enrolled students')
        detail_response = self.client.get(reverse('courses:detail', args=[pending.pk]))
        self.assertEqual(detail_response.status_code, 403)

    def test_student_course_detail_shows_submitted_for_attempted_quiz(self):
        course = Course.objects.create(name='AI/ML', faculty=self.faculty)
        quiz = Quiz.objects.create(
            title='Machine Learning Quiz',
            course=course,
            is_published=True,
        )
        Attempt.objects.create(
            quiz=quiz,
            student=self.student,
            score=10,
            is_graded=True,
            is_released=True,
        )
        self.client.force_login(self.student)

        response = self.client.get(reverse('courses:detail', args=[course.pk]))

        self.assertContains(response, 'Submitted')
        self.assertNotContains(response, 'Start quiz')

    def test_admin_cannot_create_course(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('courses:create'))
        self.assertEqual(response.status_code, 403)
