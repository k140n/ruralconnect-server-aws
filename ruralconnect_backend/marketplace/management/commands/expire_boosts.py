from django.core.management.base import BaseCommand
from marketplace.models import sync_expired_boosts, Boost, Product


class Command(BaseCommand):
    help = 'Expires past seller boosts and resets product promoted status.'

    def handle(self, *args, **options):
        self.stdout.write('Synchronizing expired boosts...')
        sync_expired_boosts()
        active_count = Boost.objects.filter(status=Boost.STATUS_ACTIVE).count()
        promoted_count = Product.objects.filter(promoted=True).count()
        self.stdout.write(self.style.SUCCESS(
            f'Done. Active boosts remaining: {active_count}, Promoted products: {promoted_count}'
        ))

