from django.db.models.signals import post_save
from django.dispatch import receiver
from projects.models import Project
from .models import DepartmentStatus, DepartmentStatusHistory 
from chatbot.vector_store import add_document


@receiver(post_save, sender=Project)
def create_department_statuses(sender, instance, created, **kwargs):
    """À la création d'un projet, crée automatiquement les 6 lignes de département."""
    if created:
        for dept_code, _ in DepartmentStatus.Department.choices:
            DepartmentStatus.objects.get_or_create(project=instance, department=dept_code)
            



@receiver(post_save, sender=DepartmentStatusHistory)
def index_status_comment(sender, instance, **kwargs):
    if instance.comment and instance.comment.strip():
        add_document(
            doc_id=f"status_history_{instance.pk}",
            text=instance.comment,
            metadata={
                "project_id": instance.department_status.project_id,
                "source_type": "status_comment",
                "department": instance.department_status.department,
            }
        )