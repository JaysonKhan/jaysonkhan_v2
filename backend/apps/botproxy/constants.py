"""Centralized UI strings for bot admin panel."""


class BotAdminMessages:
    # Staff
    STAFF_CREATED = "Xodim qo'shildi: {name}"
    STAFF_UPDATED = "Xodim yangilandi"
    STAFF_DELETED = "Xodim o'chirildi"

    # Polls
    POLL_CREATED = "So'rovnoma yaratildi: {title}"
    POLL_DELETED = "So'rovnoma o'chirildi"
    POLL_CLOSED = "Poll yopildi"

    # Channels
    CHANNEL_ADDED = "Majburiy kanal qo'shildi: {channel}"
    CHANNEL_REMOVED = "Kanal o'chirildi: {channel}"
    POSTS_REFRESHED = "Barcha kanal postlari muvaffaqiyatli yangilandi!"

    # Admins
    ADMIN_ADDED = "{role} qo'shildi: {user_id}"
    ADMIN_REMOVED = "Admin o'chirildi: {user_id}"

    # Universities
    UNIVERSITY_UPDATED = "Universitet yangilandi"
    UNIVERSITY_DELETED = "Universitet o'chirildi"
    FACULTY_ADDED = "Fakultet qo'shildi: {code}"
    FACULTY_REMOVED = "Fakultet o'chirildi"

    # Validation
    REQUIRED_FIELDS = "Nomi, tavsif va muddati to'ldirilishi shart"
    MIN_CANDIDATE = "Kamida bitta nomzod kiritilishi kerak"
    USER_NOT_FOUND = "User {user_id} topilmadi"
    LOGO_TOO_LARGE = "Ma'lumot yangilandi, lekin logo 5MB dan katta"
    LOGO_UPLOAD_FAILED = "Ma'lumot yangilandi, lekin logo yuklanmadi"
