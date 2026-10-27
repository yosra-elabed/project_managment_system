from django.conf import settings
from django.db import models
from projects.models import Project


class Task(models.Model):
    """Open Item / Tâche liée à un projet et assignée à un utilisateur."""

    class Status(models.TextChoices):
        TODO = 'TODO', 'À faire'
        IN_PROGRESS = 'IN_PROGRESS', 'En cours'
        DONE = 'DONE', 'Terminée'
        EXTRA = 'EXTRA', 'Extra'

    title = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Projet",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assigned_tasks',
        verbose_name="Responsable",
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.TODO,
        verbose_name="Statut",
    )

    due_date = models.DateField(null=True, blank=True, verbose_name="Échéance")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Tâche"
        verbose_name_plural = "Tâches"

    def __str__(self):
        return self.title