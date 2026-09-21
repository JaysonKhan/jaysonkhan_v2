"""Localized labels and configuration for the shared discussion component."""
from django.conf import settings
from django.utils.translation import gettext as _


def discussion_labels():
    return {
        'deleteComment': _('Delete comment'), 'deleteTitle': _('Delete this comment?'),
        'deleteHint': _('Other replies will stay. You can undo this for 60 seconds.'),
        'delete': _('Delete'), 'cancel': _('Cancel'), 'undo': _('Undo'),
        'deleted': _('Comment deleted.'), 'restored': _('Comment restored.'),
        'pendingReply': _('Your reply is pending review.'),
        'writeReply': _('Write a reply…'), 'postReply': _('Post reply'),
        'actions': _('Comment actions'), 'readMore': _('Read more'), 'showLess': _('Show less'),
        'reply': _('Reply'), 'replies': _('Replies'), 'hideReplies': _('Hide replies'),
        'earlierReplies': _('Load earlier replies'), 'moreReplies': _('Load more replies'), 'moreComments': _('Load more comments'),
        'loading': _('Loading…'), 'sending': _('Sending…'), 'send': _('Send comment'),
        'empty': _('No comments yet — be the first to share your thoughts.'),
        'loadFailed': _("Couldn't load comments."), 'retry': _('Retry'),
        'genericError': _('Something went wrong. Please try again.'),
        'networkError': _('Network error. Please try again.'),
        'login': _('Sign in with Telegram to join the discussion.'),
        'signingIn': _('Signing in…'), 'you': _('You'), 'react': _('Add reaction'),
        'image': _('Comment image'), 'close': _('Close'),
        'replyingTo': _('Replying to {name}'),
        'imageHint': _('JPG, PNG, GIF or WEBP, up to {n} MB.'),
        'minChars': _('Write at least {n} characters, or attach an image.'),
        'maxChars': _('Keep your comment within {n} characters.'),
        'draftRestored': _('Your draft has been restored.'),
        'link': _('Link to comment'), 'likes': _('likes'),
        'noLogin': _('Telegram sign-in is temporarily unavailable.'),
    }


def discussion_limits():
    return {
        'minLength': getattr(settings, 'COMMENT_MIN_LENGTH', 3),
        'maxLength': getattr(settings, 'COMMENT_MAX_LENGTH', 1000),
        'maxImageMB': getattr(settings, 'COMMENT_MAX_IMAGE_MB', 5),
    }
