from django.core.management.base import BaseCommand
from apps.videos.models import Category

class Command(BaseCommand):
    help = "Create or update Vidora's starter category labels; does not create videos or users."
    def handle(self, *args, **options):
        categories = [("التقنية", "technology"), ("البرمجة", "programming"), ("الذكاء الاصطناعي", "artificial-intelligence"), ("الألعاب", "gaming"), ("التعليم", "education"), ("الرياضة", "sports"), ("الموسيقى", "music")]
        for order, (name, slug) in enumerate(categories):
            Category.objects.update_or_create(slug=slug, defaults={"name": name, "is_active": True, "sort_order": order})
        self.stdout.write(self.style.SUCCESS(f"Prepared {len(categories)} categories."))
