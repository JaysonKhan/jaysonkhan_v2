from .models import ContactMessage

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
        # Here you could add logic to send an email notification as well
        return self.repository.create_message(name, email, subject, message)
