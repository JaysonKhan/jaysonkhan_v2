"""Labels for code-owned project metrics; values/dates live in Project.stats."""
from django.utils.translation import gettext as _


def metric_label(label):
    labels = {
        "Published questions": _("Published questions"),
        "Registered users": _("Registered users"),
        "Mobile apps": _("Mobile apps"),
        "Telegram users": _("Telegram users"),
        "University listings": _("University listings"),
        "Universities with scores": _("Universities with scores"),
    }
    return labels.get(label, label)
