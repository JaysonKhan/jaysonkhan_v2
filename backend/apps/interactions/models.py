from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class TelegramProfile(models.Model):
    """
    Stores Telegram user data received from Login Widget.
    Not linked to Django's User model — auth is session-based.
    """
    telegram_id  = models.BigIntegerField(unique=True)
    first_name   = models.CharField(max_length=150)
    last_name    = models.CharField(max_length=150, blank=True)
    username     = models.CharField(max_length=150, blank=True)
    photo_url    = models.URLField(blank=True)
    auth_date    = models.IntegerField()          # unix timestamp from Telegram
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Telegram Profile'
        verbose_name_plural = 'Telegram Profiles'

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        return self.full_name or self.username or f"User #{self.telegram_id}"

    def __str__(self):
        return self.display_name


class Comment(models.Model):
    """
    Generic comment that can be attached to any model (Post, Project, …).
    By default, comments are auto-approved (visible to all).
    Admin can mark them as reviewed via the 'is_reviewed' field.
    """
    author       = models.ForeignKey(
        TelegramProfile, on_delete=models.CASCADE, related_name='comments'
    )
    # Generic relation — works with Blog Post and Project
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id    = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    text         = models.TextField(max_length=1000)
    # Telegram-like features
    parent       = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    image        = models.ImageField(upload_to='comments/images/', null=True, blank=True)
    
    is_approved  = models.BooleanField(
        default=True,
        help_text='If False, the comment is hidden from users.'
    )
    is_reviewed  = models.BooleanField(
        default=False,
        help_text='Marked as True when an admin has seen/approved this comment manually.'
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['created_at']
        verbose_name        = 'Comment'
        verbose_name_plural = 'Comments'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.author.display_name}: {self.text[:50]}"


class CommentReaction(models.Model):
    """
    Store specific emoji reactions for individual comments.
    """
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions')
    author  = models.ForeignKey(TelegramProfile, on_delete=models.CASCADE)
    emoji   = models.CharField(max_length=20) # e.g. 👍, ❤, 🔥, 😂, 👎, 😱
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('comment', 'author')
        verbose_name = 'Comment Reaction'
        verbose_name_plural = 'Comment Reactions'

    def __str__(self):
        return f"{self.author.display_name} reacted {self.emoji} on {self.comment.id}"


class Like(models.Model):
    """
    Generic like (heart) — one per Telegram user per object.
    """
    author       = models.ForeignKey(
        TelegramProfile, on_delete=models.CASCADE, related_name='likes'
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id    = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together     = ('author', 'content_type', 'object_id')
        verbose_name        = 'Like'
        verbose_name_plural = 'Likes'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.author.display_name} ❤ {self.content_type} #{self.object_id}"
