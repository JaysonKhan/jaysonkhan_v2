from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError


class UserModelTest(TestCase):
    def test_email_must_be_unique(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username='user-one',
            email='duplicate@example.com',
            password='secret123',
        )

        with self.assertRaises(IntegrityError):
            user_model.objects.create_user(
                username='user-two',
                email='duplicate@example.com',
                password='secret123',
            )
