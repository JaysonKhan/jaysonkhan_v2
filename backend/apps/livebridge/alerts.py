"""Telegram notes to the owner's admin group for what needs a person: an order that matched no account or
package, a refund for an unknown order, a deletion request. Ids only — never e-mails, tokens or bodies."""


def owner_alert(kind: str, **ids) -> None:
    from interactions.notifications.service import NotificationService, fire_and_forget

    fire_and_forget(lambda: NotificationService().log_livebridge(kind, **ids))
