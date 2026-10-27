from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from statuses.models import DepartmentStatusHistory


class Command(BaseCommand):
    help = "Supprime les rapports de statut non validés (brouillons) plus vieux que N jours."

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help="Âge maximal des brouillons en jours (défaut : 7)")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options['days'])
        drafts = DepartmentStatusHistory.objects.filter(is_released=False, changed_at__lt=cutoff)
        count = drafts.count()
        drafts.delete()
        self.stdout.write(self.style.SUCCESS(f"{count} brouillon(s) supprimé(s) (plus vieux que {options['days']} jours)."))