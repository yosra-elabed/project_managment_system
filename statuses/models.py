from django.conf import settings
from django.db import models
from projects.models import Project


class DepartmentStatus(models.Model):
    """Statut RAG (Rouge/Orange/Vert) d'un département pour un projet donné."""

    class Department(models.TextChoices):
        DND = 'DND', 'D&D'
        QUALITY = 'QUALITY', 'Quality'
        SALES = 'SALES', 'Sales'
        LOGISTICS = 'LOGISTICS', 'Logistics'
        IT = 'IT', 'IT'
        HR = 'HR', 'HR'

    class RAGStatus(models.TextChoices):
        GREEN = 'GREEN', 'Vert'
        ORANGE = 'ORANGE', 'Orange'
        RED = 'RED', 'Rouge'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='department_statuses',
    )
    department = models.CharField(max_length=20, choices=Department.choices)
    status = models.CharField(
        max_length=10,
        choices=RAGStatus.choices,
        default=RAGStatus.GREEN,
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='department_status_responsibilities',
        verbose_name="Responsable",
    )
    comment = models.TextField(blank=True, verbose_name="Commentaire")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'department')
        ordering = ['department']
        verbose_name = "Statut Département"
        verbose_name_plural = "Statuts Départements"
class DepartmentStatusHistory(models.Model):
    """Trace chaque changement de statut d'un département pour un projet."""

    department_status = models.ForeignKey(
        DepartmentStatus,
        on_delete=models.CASCADE,
        related_name='history',
    )
    status = models.CharField(
        max_length=10,
        choices=DepartmentStatus.RAGStatus.choices,
    )
    comment = models.TextField(blank=True, verbose_name="Commentaire")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='department_status_changes',
        verbose_name="Modifié par",
    )
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de modification")
    is_released = models.BooleanField(default=False)
    released_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-changed_at']
        verbose_name = "Historique de statut département"
        verbose_name_plural = "Historiques de statuts départements"

    def __str__(self):
        return f"{self.department_status.project.name} — {self.department_status.get_department_display()} → {self.get_status_display()}"
   
    