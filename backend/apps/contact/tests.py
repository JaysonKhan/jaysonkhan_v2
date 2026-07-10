from unittest.mock import patch

from contact.models import ContactMessage
from contact.services import ContactRepository, ContactService
from django.contrib.auth import get_user_model
from django.test import TestCase


class ContactServiceTest(TestCase):
    @patch('contact.services.send_mail')
    def test_send_contact_message_saves_and_sends_notifications(self, mock_send_mail):
        service = ContactService(ContactRepository())
        message = service.send_contact_message(
            name='Alice',
            email='alice@example.com',
            subject='Hello',
            message='Need a mobile app quote',
        )

        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(message.email, 'alice@example.com')
        self.assertEqual(mock_send_mail.call_count, 2)


class ContactApiPermissionsTest(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username='apiadmin',
            email='apiadmin@example.com',
            password='secret123',
            is_staff=True,
            is_superuser=True,
        )

    def test_contact_create_is_public(self):
        response = self.client.post(
            '/api/contact/',
            {
                'name': 'Bob',
                'email': 'bob@example.com',
                'subject': 'Question',
                'message': 'How soon can we start?',
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_contact_list_requires_admin_auth(self):
        anon_response = self.client.get('/api/contact/')
        self.assertIn(anon_response.status_code, (401, 403))

        # USERNAME_FIELD is email (custom User) — SimpleJWT expects it, not username
        token_response = self.client.post(
            '/api/token/',
            {'email': 'apiadmin@example.com', 'password': 'secret123'},
            content_type='application/json',
        )
        self.assertEqual(token_response.status_code, 200)
        access = token_response.json()['access']

        auth_response = self.client.get(
            '/api/contact/',
            HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(auth_response.status_code, 200)
