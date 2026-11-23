from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class ConcurrentLoginTests(TestCase):
    def test_two_users_can_remain_logged_in_in_separate_sessions(self):
        User.objects.create_user(username='first', password='password')
        User.objects.create_user(username='second', password='password')
        first_client = self.client_class()
        second_client = self.client_class()

        self.assertTrue(first_client.login(username='first', password='password'))
        self.assertTrue(second_client.login(username='second', password='password'))

        first_response = first_client.get(reverse('users:home'))
        second_response = second_client.get(reverse('users:home'))
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertContains(first_response, 'Sign out')
        self.assertContains(second_response, 'Sign out')
        self.assertEqual(
            first_response.wsgi_request.user.username,
            'first',
        )
        self.assertEqual(
            second_response.wsgi_request.user.username,
            'second',
        )

    def test_admin_overview_hides_removed_counts_and_sections(self):
        admin = User.objects.create_user(
            username='admin', password='password', role='ADMIN',
        )
        User.objects.create_user(
            username='faculty',
            password='password',
            role='FACULTY',
            first_name='Faculty',
            last_name='Member',
            email='faculty@example.com',
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('users:home'))

        self.assertEqual(response.context['faculty_count'], 1)
        self.assertContains(response, 'Registered faculty members')
        self.assertContains(response, 'Faculty Information')
        self.assertContains(response, 'faculty@example.com')
        self.assertNotContains(response, 'Submissions')
        self.assertNotContains(response, 'Review Attempts')
        self.assertNotContains(response, 'Pending Release')
        self.assertNotContains(response, 'Available Faculties')
        self.assertNotContains(response, 'Create Course')
        self.assertNotContains(response, 'View All Quizzes')
        self.assertNotContains(response, 'Question bank')
