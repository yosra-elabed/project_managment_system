from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

class Project(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = 'NOT_STARTED', 'Non commencé'
        IN_PROGRESS = 'IN_PROGRESS', 'En cours'
        ON_HOLD = 'ON_HOLD', 'En attente'
        COMPLETED = 'COMPLETED', 'Terminé'
        CANCELLED = 'CANCELLED', 'Annulé'

    class ProjectClass(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer Project'
        INTERNAL = 'INTERNAL', 'Internal Project'
        RND = 'RND', 'R&D Project'

    class ProjectType(models.TextChoices):
        NEW_DEV = 'NEW_DEV', 'New Development'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'
        IMPROVEMENT = 'IMPROVEMENT', 'Improvement'

    class AccountName(models.TextChoices):
        BMW = 'BMW', 'BMW Group'
        MERCEDES = 'MERCEDES', 'Mercedes-Benz Group'
        VW = 'VW', 'Volkswagen Group'
        STELLANTIS = 'STELLANTIS', 'Stellantis'
        OTHER = 'OTHER', 'Other'

    name = models.CharField(max_length=200, verbose_name="Project Name")
    project_class = models.CharField(
        max_length=20,
        choices=ProjectClass.choices,
        default=ProjectClass.CUSTOMER,
        verbose_name="Project Class",
    )
    project_type = models.CharField(
        max_length=20,
        choices=ProjectType.choices,
        default=ProjectType.NEW_DEV,
        verbose_name="Project Type",
    )
    account_name = models.CharField(
        max_length=20,
        choices=AccountName.choices,
        default=AccountName.OTHER,
        verbose_name="Account Name",
    )

    owner = models.CharField(
        max_length=255,
        verbose_name="Project Owner",
        blank=True,
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='managed_projects',
        limit_choices_to={'role': 'PM'},
        verbose_name="Project Manager",
    )

    description = models.TextField(blank=True, verbose_name="Description")
    targets = models.TextField(blank=True, verbose_name="Targets")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    start_date = models.DateField(null=True, blank=True, verbose_name="Start Date")
    end_date = models.DateField(null=True, blank=True, verbose_name="End Date")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    RAG_PRIORITY = {'RED': 3, 'ORANGE': 2, 'GREEN': 1}

    @property
    def global_rag_status(self):
        statuses = list(self.department_statuses.values_list('status', flat=True))
        if not statuses:
            return None
        return max(statuses, key=lambda s: self.RAG_PRIORITY.get(s, 0))

    @property
    def duration_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None

    @property
    def duration_display(self):
        days = self.duration_days
        if days is None:
            return None
        if days < 0:
            return "Dates incohérentes"
        if days < 31:
            return f"{days} jour{'s' if days > 1 else ''}"
        months = days // 30
        remaining_days = days % 30
        if months < 12:
            if remaining_days == 0:
                return f"{months} mois"
            return f"{months} mois et {remaining_days} jour{'s' if remaining_days > 1 else ''}"
        years = months // 12
        remaining_months = months % 12
        if remaining_months == 0:
            return f"{years} an{'s' if years > 1 else ''}"
        return f"{years} an{'s' if years > 1 else ''} et {remaining_months} mois"

    @property
    def effective_manager(self):
        active_delegation = self.delegations.filter(is_active=True).first()
        if active_delegation and active_delegation.is_current:
            return active_delegation.deputy
        return self.manager

    @property
    def active_delegation(self):
        for d in self.delegations.filter(is_active=True):
            if d.is_current:
                return d
        return None

    @property
    def contributors(self):
        from django.db.models import Count
        return get_user_model().objects.filter(
            assigned_tasks__project=self
        ).annotate(
            task_count=Count('assigned_tasks', filter=models.Q(assigned_tasks__project=self))
        ).distinct()

    @property
    def contributor_count(self):
        return self.contributors.count()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Project"
        verbose_name_plural = "Projects"


class Delegation(models.Model):
    delegator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegations_given',
        verbose_name="Délègue de",
    )
    deputy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delegations_received',
        verbose_name="Responsable temporaire",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='delegations',
        verbose_name="Projet",
    )
    reason = models.CharField(max_length=255, blank=True, verbose_name="Motif")
    start_date = models.DateField(default=timezone.now, verbose_name="Début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Fin (optionnel)")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Délégation"
        verbose_name_plural = "Délégations"

    def __str__(self):
        return f"{self.delegator} → {self.deputy} sur {self.project}"

    @property
    def is_current(self):
        if not self.is_active:
            return False
        today = timezone.now().date()
        if self.start_date and self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True