import logging
from django.core.mail import send_mail
from django.conf import settings
from .models import ContactMessage

logger = logging.getLogger(__name__)


class ContactRepository:
    @staticmethod
    def create_message(name, email, subject, message):
        return ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )


class ContactService:
    def __init__(self, repository: ContactRepository):
        self.repository = repository

    def send_contact_message(self, name, email, subject, message):
        """
        1. Save message to DB
        2. Send confirmation email to user
        3. Send notification to site owner
        """
        msg = self.repository.create_message(name, email, subject, message)

        # Send confirmation to the person who submitted the form
        self._send_confirmation_email(name, email)

        # Notify site owner
        self._send_notification_email(name, email, subject, message)

        return msg

    @staticmethod
    def _send_confirmation_email(name, email):
        """Send a confirmation email to the person who submitted the form."""
        try:
            send_mail(
                subject="Thanks for reaching out!",
                message=(
                    f"Hi {name},\n\n"
                    "Thank you for your message! I've received it and will "
                    "get back to you as soon as possible.\n\n"
                    "Best regards,\n"
                    "Jahongir Kuziboev"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception as exc:
            logger.warning("Failed to send confirmation email to %s: %s", email, exc)

    @staticmethod
    def _send_notification_email(name, email, subject, message):
        """Notify the site owner about the new contact message."""
        try:
            from core.services import SiteSettingsService
            site = SiteSettingsService.get()
            owner_email = site.email

            if not owner_email:
                return

            send_mail(
                subject=f"[Contact Form] {subject}",
                message=(
                    f"New contact form submission:\n\n"
                    f"Name: {name}\n"
                    f"Email: {email}\n"
                    f"Subject: {subject}\n\n"
                    f"Message:\n{message}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[owner_email],
                fail_silently=True,
            )
        except Exception as exc:
            logger.warning("Failed to send notification email: %s", exc)
