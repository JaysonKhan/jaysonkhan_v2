from unittest.mock import patch

from contact.models import ContactMessage
from contact.services import ContactRepository, ContactService
from contact.spam_protection import is_valid_contact
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse


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


class ContactFormSpamTest(TestCase):
    """Regression cover for the 2026-06..08 bulk-spam wave (32 of 35 messages).

    Samples below are verbatim from what actually landed in production.
    """

    def setUp(self):
        # The per-IP rate limit is cache-backed and every test client request
        # shares one IP — without this, the 4th post in the class 429s.
        cache.clear()
        self.url = reverse('contact')

    def _post(self, **overrides):
        data = {'name': 'Alice', 'email': 'alice@example.com',
                'message': 'Need a mobile app quote'}
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_valid_contact_accepts_email_and_telegram_handle(self):
        self.assertTrue(is_valid_contact('raximjonr105@gmail.com'))
        self.assertTrue(is_valid_contact('@murodillo17'))

    def test_valid_contact_rejects_bot_garbage(self):
        self.assertFalse(is_valid_contact('@xqhjtxbh a oxips'))
        self.assertFalse(is_valid_contact('not-an-email'))

    @patch('contact.services.send_mail')
    def test_real_enquiry_is_saved(self, mock_send_mail):
        response = self._post(email='@jumayev_2k',
                              message="bu platforma nechanchi yilgi ma'lumot")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(mock_send_mail.call_count, 2)

    @patch('contact.services.send_mail')
    def test_garbage_contact_is_rejected_and_not_stored(self, mock_send_mail):
        self._post(email='@xqhjtxbh a oxips', message='Test, message - Thank you!')
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertEqual(mock_send_mail.call_count, 0)

    @patch('contact.services.send_mail')
    def test_link_blast_is_dropped_silently(self, mock_send_mail):
        response = self._post(message=(
            'https://mega.nz/file/3m5GTSoR https://telegra.ph/confidental-report '
            'https://im.ge/i/QMKop8M read this'
        ))
        self.assertEqual(response.status_code, 200)
        # Bot must see the same success page a human gets — an error tells the
        # sender their payload was fingerprinted, so they retune it.
        self.assertTrue(response.context['success'])
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertEqual(mock_send_mail.call_count, 0)

    @patch('contact.services.send_mail')
    def test_spam_phrase_is_dropped_silently(self, mock_send_mail):
        self._post(message='The $27,000,000 Jackpot Is a Whisper from Destiny')
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertEqual(mock_send_mail.call_count, 0)

    @patch('contact.services.send_mail')
    def test_honeypot_field_is_no_longer_named_website(self, mock_send_mail):
        # 'website' is now an ordinary ignored field; only 'referral_code' baits.
        self._post(website='http://bot.example')
        self.assertEqual(ContactMessage.objects.count(), 1)

        cache.clear()
        self._post(referral_code='http://bot.example')
        self.assertEqual(ContactMessage.objects.count(), 1)
