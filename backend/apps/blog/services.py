from .models import Post, Category, Tag

class BlogRepository:
    @staticmethod
    def get_published_posts():
        return Post.objects.filter(is_published=True).select_related('category', 'author').prefetch_related('tags')

    @staticmethod
    def get_post_by_slug(slug):
        try:
            return Post.objects.select_related('category', 'author').prefetch_related('tags').get(slug=slug, is_published=True)
        except Post.DoesNotExist:
            return None

    @staticmethod
    def get_categories():
        return Category.objects.all()

class BlogService:
    def __init__(self, repository: BlogRepository):
        self.repository = repository

    def get_all_published_posts(self):
        return self.repository.get_published_posts()

    def get_post_details(self, slug):
        return self.repository.get_post_by_slug(slug)
