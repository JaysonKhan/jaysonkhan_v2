"""Modeltranslation registrations for blog models."""
from modeltranslation.translator import register, TranslationOptions
from .models import Post, Category, Tag


@register(Post)
class PostTranslation(TranslationOptions):
    fields = (
        'title',
        'excerpt',
        'content_rich',
    )


@register(Category)
class CategoryTranslation(TranslationOptions):
    fields = ('name',)


@register(Tag)
class TagTranslation(TranslationOptions):
    fields = ('name',)
