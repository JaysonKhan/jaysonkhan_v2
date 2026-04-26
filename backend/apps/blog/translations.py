"""Modeltranslation registrations for blog models."""
from modeltranslation.translator import register, TranslationOptions
from .models import Post, Category, Tag


@register(Post)
class PostTranslation(TranslationOptions):
    fallback_undefined = ''
    fields = (
        'title',
        'excerpt',
        'content_rich',
    )


@register(Category)
class CategoryTranslation(TranslationOptions):
    fallback_undefined = ''
    fields = ('name',)


@register(Tag)
class TagTranslation(TranslationOptions):
    fallback_undefined = ''
    fields = ('name',)
