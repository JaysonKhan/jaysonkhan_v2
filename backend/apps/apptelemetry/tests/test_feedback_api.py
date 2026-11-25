"""POST /api/services/v1/feedback/ and the owner's Telegram note."""
import uuid
from unittest import mock

from apptelemetry.models import AppFeedback, AppInstall
from interactions.notifications.service import NotificationService

from .helpers import FEEDBACK_URL, ServicesTestCase, turn


def feedback(**extra):
    body = {'app': 'livebridge', 'app_version': '1.0.0+1', 'ui_language': 'uz',
            'message': "Tarjima tez, lekin qisqa so'zlarni noto'g'ri eshitadi."}
    body.update(extra)
    return body


class FeedbackApiTest(ServicesTestCase):
    def assertError(self, response, code):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': code})

    def test_happy_path_links_a_known_install(self):
        install_id = str(uuid.uuid4())
        self.send([turn()], install_id)
        with mock.patch('apptelemetry.services._notify_owner') as notify:
            response = self.post_json(FEEDBACK_URL, feedback(install_id=install_id, email='a@example.com', rating=4))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {'ok': True})
        row = AppFeedback.objects.get()
        self.assertEqual((row.app, row.rating, row.email, row.app_version, row.ui_language),
                         ('livebridge', 4, 'a@example.com', '1.0.0+1', 'uz'))
        self.assertEqual(row.install, AppInstall.objects.get(install_id=install_id))
        notify.assert_called_once_with(row)

    def test_minimal_feedback_without_optional_fields(self):
        response = self.post_json(FEEDBACK_URL, {'app': 'livebridge', 'message': 'ok', 'email': '', 'rating': None})
        self.assertEqual(response.status_code, 201)
        row = AppFeedback.objects.get()
        self.assertEqual((row.email, row.rating, row.install), ('', None, None))

    def test_message_is_required_and_capped(self):
        self.assertError(self.post_json(FEEDBACK_URL, feedback(message=None)), 'bad_message')
        self.assertError(self.post_json(FEEDBACK_URL, {'app': 'livebridge'}), 'bad_message')
        self.assertError(self.post_json(FEEDBACK_URL, feedback(message='   ')), 'bad_message')
        self.assertError(self.post_json(FEEDBACK_URL, feedback(message='x' * 2001)), 'bad_message')
        self.assertEqual(self.post_json(FEEDBACK_URL, feedback(message='x' * 2000)).status_code, 201)

    def test_envelope_rules(self):
        self.assertError(self.post_json(FEEDBACK_URL, 'nope'), 'bad_json')
        self.assertError(self.post_json(FEEDBACK_URL, feedback(app='other')), 'unknown_app')
        self.assertError(self.post_json(FEEDBACK_URL, feedback(install_id='123')), 'bad_install_id')

    def test_email_validation(self):
        self.assertError(self.post_json(FEEDBACK_URL, feedback(email='not-an-email')), 'bad_email')
        self.assertError(self.post_json(FEEDBACK_URL, feedback(email='a' * 250 + '@x.io')), 'bad_email')
        self.assertError(self.post_json(FEEDBACK_URL, feedback(email=42)), 'bad_email')

    def test_rating_validation(self):
        for bad in (0, 6, '5', 4.5, True):
            with self.subTest(rating=bad):
                self.assertError(self.post_json(FEEDBACK_URL, feedback(rating=bad)), 'bad_rating')
        self.assertEqual(AppFeedback.objects.count(), 0)

    def test_rate_limit_is_five_per_address_per_hour(self):
        for _ in range(5):
            self.assertEqual(self.post_json(FEEDBACK_URL, feedback()).status_code, 201)
        response = self.post_json(FEEDBACK_URL, feedback())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {'error': 'rate_limited'})
        self.assertTrue(int(response['Retry-After']) > 0)
        self.assertEqual(self.post_json(FEEDBACK_URL, feedback(), ip='198.51.100.9').status_code, 201)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(FEEDBACK_URL).status_code, 405)


class FeedbackNotificationTest(ServicesTestCase):
    def test_owner_note_has_no_email_and_a_capped_message(self):
        row = AppFeedback.objects.create(app='livebridge', message='<b>' + 'y' * 900, email='secret@example.com',
                                         rating=2, app_version='1.0.0+1')
        with mock.patch.object(NotificationService, '_send_to_admin_group') as send, \
                mock.patch('interactions.notifications.service.TelegramBotAPI'):
            NotificationService().log_service_feedback(row)
        text = send.call_args.args[0]
        self.assertNotIn('secret@example.com', text)
        self.assertNotIn('<b>yyy', text)  # escaped
        self.assertIn('&lt;b&gt;', text)
        self.assertIn('2/5', text)
        self.assertLess(text.count('y'), 520)
        self.assertIn(f'/apptelemetry/appfeedback/{row.pk}/change/', send.call_args.kwargs['reply_markup']['inline_keyboard'][0][0]['url'])
