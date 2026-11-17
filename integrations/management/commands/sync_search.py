from django.core.management.base import BaseCommand
from integrations.search import refresh_search
class Command(BaseCommand):
    help = 'Refresh the public article index (no private fields). Run only one sync at a time.'
    def handle(self, **options):
        from integrations.tasks import refresh_search as task
        self.stdout.write(f'Indexed {task()} public stories.')
